"""
CycloMonitor - ATCF and IBTrACS wrapper for Discord
Copyright (c) 2023 Virtual Nate

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
details.

For those hosting a copy of this bot, you should have received a copy of the
GNU Affero General Public License along with this program. If not, see
<https://www.gnu.org/licenses/>.
"""

from . import cli
import datetime
import logging
import asyncio
from sys import exit
from .locales import *

logname = "bot.log"
# PLEASE CHANGE THESE LINKS IF YOU ARE FORKING THIS PROJECT.
INVITE = "https://discord.com/api/oauth2/authorize?client_id={0}&permissions=67496000&scope=bot"
GITHUB = "GITHUB_LINK"
SERVER = "SERVER_INVITE"
emojis = {}

# increase compatibility with python<3.11
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc

try:
    from tendo import singleton
except ImportError:
    singleton = None

try:
    from . import cyclomonitor
    from .cyclomonitor import bot
except ImportError:
    bot = None


def main():
    import argparse
    import json

    global GITHUB, INVITE, SERVER
    locale_init()
    parser = argparse.ArgumentParser(
        prog="cyclomonitor",
        description=DESCRIPTION,
        epilog=HELP_EPILOG.format(GITHUB),
    )
    parser.add_argument("-b", "--bot", help=HELP_BOT, action="store_true")
    parser.add_argument("-t", "--token", help=HELP_TOKEN, default="")
    parser.add_argument(
        "-i", "--interactive", help=HELP_INTERACTIVE, action="store_true"
    )
    parser.add_argument("-l", "--log-file", help=HELP_LOG_FILE, default="")
    parser.add_argument("-v", "--verbose", help=HELP_VERBOSE, action="store_true")
    parser.add_argument("-c", "--config", help=HELP_CONFIG, default="")
    args = parser.parse_args()
    log_params = {}

    if args.bot or args.token:
        run_bot = True
        # support the legacy TOKEN file
        try:
            with open("TOKEN", "r") as f:
                _token = f.read().split()[0]  # split in case of any newlines or spaces
        except FileNotFoundError:
            pass

        if args.token:
            _token = args.token
    else:
        run_bot = False
    if run_bot and args.interactive:
        raise ValueError(ERROR_BOT_AND_INTERACTIVE)

    if args.log_file:
        log_params["filename"] = args.log_file
        log_params["filemode"] = "a"

    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        _token = config["token"]
        if config.get("log_file") is not None:
            log_params["filename"] = config["log_file"]
            log_params["filemode"] = "a"
            logging.captureWarnings(True)
        if config.get("github") is not None:
            GITHUB = config["github"]
        if config.get("client_id") is not None:
            INVITE = INVITE.format(config["client_id"])
        if config.get("server") is not None:
            SERVER = config["server"]
        if isinstance(config.get("emojis"), dict):
            emojis.update(config["emojis"])
    if args.verbose:
        log_params["level"] = logging.DEBUG
    else:
        log_params["level"] = logging.INFO
    logging.basicConfig(
        format="%(asctime)s.%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        **log_params,
    )
    if args.bot:
        if bot is None:
            raise ModuleNotFoundError(ERROR_PYCORD_MISSING)
        if singleton is None:
            raise ModuleNotFoundError(ERROR_TENDO_MISSING)

        cyclomonitor.GITHUB = GITHUB
        cyclomonitor.INVITE = INVITE
        cyclomonitor.SERVER = SERVER
        cyclomonitor.emojis = emojis

        try:
            # Prevent more than one instance from running at once
            me = singleton.SingleInstance()
        except singleton.SingleInstanceException:
            exit(ERROR_ALREADY_RUNNING)

        try:
            bot.run(_token)
        except NameError:
            raise ValueError(ERROR_NO_TOKEN)
        return
    if args.interactive:
        if args.config:
            logging.warning(LOG_BOT_CONFIG_AND_INTERACTIVE)
        if log_params.get("filename") is not None:
            raise ValueError(ERROR_LOG_FILE_AND_INTERACTIVE)
        cli.cli()
        return
    parser.print_help()


if __name__ == "__main__":
    main()
