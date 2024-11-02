from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from datetime import date, timedelta
from typing import Generic, TypeVar

import requests
from dotenv import load_dotenv
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.getenv("API_TOKEN", "")
if not TOKEN:
    raise ValueError("Missing API_TOKEN")

BASE_URL = "https://kitchen.kanttiinit.fi"

# ------------- Interface --------------------


@dataclass
class Restaurant:
    """Generic Restaurant class."""

    pass


@dataclass
class Menu:
    """Generic Menu class."""

    pass


MENU_TYPE = TypeVar("MENU_TYPE", bound=Menu)
RES_TYPE = TypeVar("RES_TYPE", bound=Restaurant)


class RestaurantManager(ABC, Generic[RES_TYPE]):
    """Restaurant manager interface."""

    _rest: dict[str, RES_TYPE] = {}

    @classmethod
    def restaurants(cls) -> dict[str, RES_TYPE]:
        """Singleton for a dictionary of restaurants."""
        if not cls._rest:
            cls._load_restaurants()
        return cls._rest

    @classmethod
    @abstractmethod
    def _load_restaurants(cls):
        raise NotImplemented()


class MenuManager(ABC, Generic[MENU_TYPE]):
    """Menu manager interface."""

    @staticmethod
    @abstractmethod
    def get_restaurant_menu(
        restaurant_id: int | str, d: str = str(date.today())
    ) -> list[MENU_TYPE]:
        raise NotImplemented


# ---------------- Class Implementations ------------


@dataclass
class KanttiinitRestaurant(Restaurant):
    """Definition of the Kanttiinit Restaurant object.

    Source schema can be found here:
        https://github.com/Kanttiinit/kitchen/blob/master/schema/restaurant.json

    Some irrelevant attributes were omitted.
    """

    id: str
    name: str
    url: str
    address: str
    openingHours: list[str]

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)


class KanttiinitRestaurantManager(RestaurantManager[KanttiinitRestaurant]):

    @classmethod
    def _load_restaurants(cls):
        res = requests.get(url=f"{BASE_URL}/areas", params={"lang": "en"})
        otamiemi_area = [area for area in json.loads(res.text) if area["name"] == "Otaniemi"]
        cls._rest = {
            str(rest["id"]): KanttiinitRestaurant(**rest)
            for rest in otamiemi_area[0]["restaurants"]
        }


@dataclass
class KanttiinitMenu(Menu):
    """Definition of the Kanttiinit Menu object.

    Source schema can be found here:
        https://github.com/Kanttiinit/kitchen/blob/master/schema/menu.json
    """
    title: str
    properties: list[str]


class KanttiinitMenuManager(MenuManager[KanttiinitMenu]):

    @staticmethod
    def get_restaurant_menu(
        restaurant_id: int | str, d: str = str(date.today())
    ) -> list[KanttiinitMenu]:
        """Get a menu for the given canteen and date."""
        res = requests.get(
            url=f"{BASE_URL}/menus",
            params={"restaurants": restaurant_id, "days": str(d), "lang": "en"},
        )
        return [
            KanttiinitMenu(**menu)
            for menu in json.loads(res.text)[str(restaurant_id)].get(d, [])
        ]


# ------------- BOT --------------------


def generate_cancel_send_buttons(callback_suffix: str) -> list[InlineKeyboardButton]:
    """Generate the cancel and send button."""
    keyboard = [
        InlineKeyboardButton("Cancel", callback_data=f"cancel_{callback_suffix}"),
        InlineKeyboardButton("Send", callback_data=f"send_{callback_suffix}"),
    ]
    return keyboard


def generate_canteen_buttons(callback_prefix: str) -> InlineKeyboardMarkup:
    """Generate the canteen picker buttons."""
    rest = list(KanttiinitRestaurantManager.restaurants().values())

    # divide buttons into two columns
    keyboard = [
        [
            InlineKeyboardButton(
                p[0].name, callback_data=f"{callback_prefix}_{p[0].id}"
            ),
            InlineKeyboardButton(
                p[1].name, callback_data=f"{callback_prefix}_{p[1].id}"
            ),
        ]
        for p in zip(rest[::2], rest[1::2])
    ]

    # if there is an odd number of canteens
    # stretch the last button across two columns
    if len(rest) % 2 == 1:
        keyboard.append(
            [
                InlineKeyboardButton(
                    rest[-1].name, callback_data=f"{callback_prefix}_{rest[-1].id}"
                ),
            ]
        )
    # add a cancel button
    keyboard.append(
        [
            InlineKeyboardButton("Cancel", callback_data=f"cancel"),
        ]
    )

    # send a reply to the command
    return InlineKeyboardMarkup(keyboard)


async def cancel_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handle the cancel button."""
    query = update.callback_query
    if not query:
        return
    await query.delete_message()


async def send_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Send the current message."""
    # input check
    query = update.callback_query
    if not query:
        return
    if not query.data:
        await query.delete_message()
        return

    op = query.data.removeprefix("send_")
    orig_msg = query.message.text
    message = "Command not found"
    if op == "opening_hours" or op == "menu":
        message = orig_msg.split("\n")
        content = "\n".join(message[1:])
        message = f"<b>{message[0]}</b>\n<code>{content}</code>"
    elif op == "link":
        message = orig_msg

    await query.edit_message_text(text=message, parse_mode=ParseMode.HTML)


async def opening_hours_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Display the opening hours for the chosen canteen."""
    # input check
    query = update.callback_query
    if not query:
        return
    if not query.data:
        await query.delete_message()
        return

    # generate all the buttons
    rest = KanttiinitRestaurantManager.restaurants()[
        query.data.removeprefix("opening_hours_")
    ]
    reply_markup = InlineKeyboardMarkup([generate_cancel_send_buttons("opening_hours")])

    # generate the message
    message = f"<b>{rest.name}</b>\n<code>"
    for oh in zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], rest.openingHours):
        message += f"{oh[0]}: {oh[1]}\n"
    message += "</code>"

    # send the message
    await query.edit_message_text(
        text=message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def opening_hours_buttons(query: CallbackQuery):
    """Display canteen picker for the opening hours option."""
    reply_markup = generate_canteen_buttons("opening_hours")
    await query.edit_message_text(
        "<b>Opening Hours</b>\nChoose the canteen:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


async def link_handler(query: CallbackQuery):
    """Handle the link message."""
    reply_markup = InlineKeyboardMarkup([generate_cancel_send_buttons("link")])
    await query.edit_message_text(
        text="https://kanttiinit.fi", reply_markup=reply_markup
    )


async def menu_canteen_handler(query: CallbackQuery):
    """Display a canteen picker."""
    reply_markup = generate_canteen_buttons("menu_canteen")

    # generate the final message
    await query.answer()
    await query.edit_message_text(
        "<b>Menu</b>\nChoose the canteen:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


async def menu_date_pick_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Display a date picker."""
    # input check
    query = update.callback_query
    if not query:
        return
    if not query.data:
        await query.delete_message()
        return

    # extract the canteen's id
    _id = query.data.removeprefix("menu_canteen_")

    # generate the date picker button
    dates = [date.today() + timedelta(days=i) for i in range(7)]
    keyboard = [
        [
            InlineKeyboardButton(
                d.strftime("%d.%m.%y (%a)"), callback_data=f"menu_date_{str(d)}|{_id}"
            )
        ]
        for d in dates
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data=f"cancel")])

    # generate the final message
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.answer()
    await query.edit_message_text(
        text="<b>Menu date</b>\nChoose the date:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


async def menu_display_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Display the menu for the chosen canteen and date."""

    def _generate_message(_id: str, _date: str) -> str:
        """Generate a message containing canteen's menu."""
        message = (
            f"<b>{KanttiinitRestaurantManager.restaurants()[_id].name} ({_date})</b>\n"
        )

        message += "<code>"
        counter = 1
        for m in KanttiinitMenuManager.get_restaurant_menu(_id, _date):
            title = m.title.strip()
            message += f"{counter}. {title}"
            counter += 1
            message += "\n"
        return message + "</code>"

    # input check
    query = update.callback_query
    if not query:
        return
    if not query.data:
        await query.delete_message()
        return
    date, _id = query.data.removeprefix("menu_date_").split("|")

    reply_markup = InlineKeyboardMarkup([generate_cancel_send_buttons("menu")])
    # update the message sent
    await query.answer()
    await query.edit_message_text(
        _generate_message(_id, date),
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


async def option_handler(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handle the chosen canteen option."""
    query = update.callback_query
    if not query or not query.data:
        return

    command = query.data.removeprefix("option_")
    if command == "link":
        await link_handler(query)
    elif command == "menu":
        await menu_canteen_handler(query)
    elif command == "opening-hours":
        await opening_hours_buttons(query)
    else:
        await query.delete_message()


async def canteens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List the canteens commands."""
    # remove the command message sent by the user
    if not update.message:
        return
    # await context.bot.delete_message(update.message.chat_id, update.message.id)

    options = ["Link", "Menu", "Opening Hours", "Cancel"]
    keyboard = [
        [InlineKeyboardButton(o, callback_data=f"option_{o.replace(' ', '-').lower()}")]
        for o in options
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Choose the action: ", reply_markup=reply_markup, disable_notification=True
    )


async def post_init(application: Application):
    """Set the command help."""
    commands = [("canteens", "Otaniemi canteen commands.")]
    await application.bot.set_my_commands(commands)


def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    # bot commands
    app.add_handler(CommandHandler("canteens", canteens))

    # bot interactive handlers
    app.add_handler(CallbackQueryHandler(option_handler, pattern="^option"))
    app.add_handler(
        CallbackQueryHandler(opening_hours_handler, pattern="^opening_hours")
    )
    app.add_handler(
        CallbackQueryHandler(menu_date_pick_handler, pattern="^menu_canteen")
    )
    app.add_handler(CallbackQueryHandler(menu_display_handler, pattern="^menu_date"))

    # back button handlers
    app.add_handler(CallbackQueryHandler(option_handler, pattern="^menu_canteen_back"))
    app.add_handler(CallbackQueryHandler(send_handler, pattern="^send"))
    app.add_handler(CallbackQueryHandler(cancel_handler, pattern="^cancel"))

    # start polling
    app.run_polling()


if __name__ == "__main__":
    main()
