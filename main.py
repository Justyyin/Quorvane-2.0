"""Entry point: loads the token and settings and starts the bot."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from quorvane import musicbot
from quorvane.core import Bot, banner
from quorvane.logsetup import setup_logging


async def start(bot, token, music, music_token):
    """Run Quorvane and, when it is set up, Quorvane Music next to it. Quorvane Music stops together with Quorvane."""
    async with bot:
        task = asyncio.create_task(musicbot.run(music, music_token)) if music else None
        try:
            await bot.start(token)
        finally:
            if music and not music.is_closed():
                await music.close()
            if task:
                await asyncio.gather(task, return_exceptions=True)


def main():
    """Read the token and settings, then start the bot."""
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        sys.exit("DISCORD_TOKEN is missing. Copy .env.example to .env and enter your bot token.")
    settings = {}
    path = Path("settings.json")
    if path.exists():
        settings = json.loads(path.read_text(encoding="utf-8"))
    print(banner())
    setup_logging(settings)
    bot = Bot(settings)
    music, music_token = None, None
    conf = musicbot.settings_of(settings)
    if conf["enabled"]:
        music_token = os.getenv(conf["token_env"])
        if music_token:
            music = bot.music_bot = musicbot.MusicBot(bot)
        else:
            logging.getLogger("quorvane").warning("music_bot is enabled but %s is missing in .env, music stays inside Quorvane", conf["token_env"])
    try:
        asyncio.run(start(bot, token, music, music_token))
    except KeyboardInterrupt:
        pass
    if bot.restart_requested:
        logging.shutdown()
        if os.name == "nt":
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
        os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    main()
