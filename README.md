# Lunch Time Coordinator Telegram Bot

This python script sends a poll to a telegram chat to coordinate the lunch time for the next day. The poll lets the users vote for the time they want to have lunch.


## Usage

After creating a bot as described in the [Telegram documentation about "BotFather"](https://core.telegram.org/bots/features#botfather), the python script [`main.py`](main.py) can be invoked while passing the bot token, the chat id and optionally the thread id (for supergroups/forums) as environment variables:

```bash
TELEGRAM_BOT_TOKEN="..." TELEGRAM_CHAT_ID="..." TELEGRAM_THREAD_ID="..." python3 lunch-coordinator-bot/main.py
```


## cron

Since running the script manually every day doesn't make it very useful, it makes sense to create a cron job that runs the script every day at a specific time (on a computer that is running at the time, e.g. a home server or a VPS). The following cron job runs the script every day at 17:00 (5pm) from Sunday to Thursday, so that there are polls for the next day's lunch, i.e. from Monday to Friday:

```
$ crontab -e
# Add the following line:
0 17 * * 0-4 env TELEGRAM_BOT_TOKEN="..." TELEGRAM_CHAT_ID="..." TELEGRAM_THREAD_ID="..." lunch-coordinator-bot/main.py
```