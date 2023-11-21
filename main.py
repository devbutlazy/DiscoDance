import os
import traceback

import disnake
from disnake.ext import commands

from config import BotInformation
from utils import custom_print


class Bot(commands.Bot):
    def __init__(self) -> None:
        super(Bot, self).__init__(
            command_prefix=BotInformation.BOT_PREFIX,
            intents=disnake.Intents.all()
        )

    async def on_ready(self) -> None:
        custom_print(
            f"https://github.com/devbutlazy/DiscoDance\n\n",
            date=False
        )
        custom_print(
            f"Logged in as {self.user}",
            suffix="starting"
        )
        custom_print(
            f"Bot Prefix: \"{BotInformation.BOT_PREFIX}\"",
            suffix="info"
        )
        for extension in os.listdir("src"):
            if extension.endswith(".py"):
                try:
                    event_name = extension[:-3]
                    self.load_extension(f"src.{event_name}")
                except (
                        commands.ExtensionNotFound,
                        commands.NoEntryPointError,
                        commands.ExtensionFailed,
                        commands.ExtensionError,
                ) as e:
                    custom_print(
                        f"\n\nFailed to load {extension}!\n{traceback.print_exception(e)}",
                        suffix="error"
                    )
                    continue
                finally:
                    custom_print(
                        f"{extension} is loaded!",
                        suffix="info"
                    )

        await self.wait_until_ready()
        await self.change_presence(
            activity=disnake.Activity(
                status=disnake.Status.idle,
                name=f"Music Bot by LazyDev",
            )
        )


if __name__ == "__main__":
    Bot().run(BotInformation.BOT_TOKEN)
