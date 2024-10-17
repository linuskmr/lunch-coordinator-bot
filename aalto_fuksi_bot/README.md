# Extended Aalto Fuksis Telegram Chat Bot

This version of the bot is capable to receive commands and answer accordingly. Since students have some difficulties deciding where to go the lunch, a new `/canteens` command was created to tackle this problem.

## Installation

In order to run the script using `python` command user has to install all the dependencies located in `requirements.txt`. If you plan to use containers instead you can skip this section.

If you are not familiar with [Python's virtual environments](https://docs.python.org/3/library/venv.html) use the following guide (may differ on the different OS):

```bash
$ cd aalto_fuksi_bot/

# init virtual environment
$ python3 -m venv .venv

# activate virtual environment
$ source .venv/bin/activate

# install dependencies
$ pip install -r requirements.txt

# run the bot script (more info in the following section)
$ python3 bot_script.py

```

## Usage

Here are two methods how to deploy the bot: either running the script using `Python` or build and run a container.

### Using CLI

After creating a bot as described in the [Telegram documentation about "BotFather"](https://core.telegram.org/bots/features#botfather), the bot server can be started by passing the *bot token* using the environment variables. The user can also create an `.env` file as the scripts also loads environment variables from it too.

```bash
API_TOKEN="..." python3 bot_main.py

# or add this to `.env` file
export API_TOKEN="..."
```

### Using containers

We also provided a `Containerfile` for the user to build their own telegram bot image. Simply use your preferable container engine to build and run the container (tested with [Podman](https://podman.io/)). Don't forget to pass the bot token using `API_TOKEN` environment variable.
```bash
podman build -t telegram-bot .

podman run -d -e API_TOKEN="..." --name telegram-bot telegram-bot:latest
```

## Supported commands

- `/canteens` - An interactive command that uses [Kanttiinit API](https://github.com/Kanttiinit/kitchen) to extract data from.
