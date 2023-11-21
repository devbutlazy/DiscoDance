import datetime
import math
from typing import Optional, Union, Any, Dict, List, Literal

import disnake
import mafic
from disnake import (
    Message,
    MessageInteraction
)
from disnake.ext import commands


class EmbedPaginator(disnake.ui.View):
    def __init__(
            self,
            interaction: Union[
                disnake.MessageCommandInteraction, disnake.MessageInteraction
            ],
            author: disnake.Member,
            embed: disnake.Embed,
            data: Optional[Union[Dict, List]],
            timeout: Optional[int] = None,
            separate: int = 10,
    ) -> None:
        super().__init__(timeout=timeout)
        self.current_page = 1
        self.interaction = interaction
        self.author: disnake.Member = author
        self.embed: disnake.Embed = embed
        self.separate = separate
        self.data = data

    async def send_message(
            self,
            ctx: Union[
                commands.Context,
                disnake.MessageCommandInteraction,
                disnake.MessageInteraction,
            ],
    ) -> Union[Message, Any]:
        if isinstance(
                ctx, (disnake.MessageCommandInteraction, disnake.MessageInteraction)
        ):
            return await ctx.response.send_message(embed=self.embed, view=self)
        return await ctx.send(embed=self.embed, view=self)

    async def _create_embed(
            self, embed: disnake.Embed, data: Union[Dict, List]
    ) -> disnake.Embed:
        embed: disnake.Embed = disnake.Embed(
            title=embed.title,
            colour=embed.colour,
            timestamp=embed.timestamp,
            description="",
        )

        for index, music in enumerate(data, start=1):
            if index > self.separate:
                break

            music: mafic.Track
            embed.description += f"`{index}.` **{music.author} - {music.title}**\n"

        all_pages = math.ceil(len(self.data) / self.separate)
        embed.set_footer(text=f"Page {self.current_page} of {all_pages}")

        return embed

    async def update(
            self,
            message: Union[disnake.MessageCommandInteraction, disnake.MessageInteraction],
            embed: disnake.Embed,
    ) -> None:
        await message.edit_original_response(embed=embed, view=self)

    @disnake.ui.button(label="️◀️", style=disnake.ButtonStyle.blurple)
    async def prev_page(
            self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ) -> None:
        await interaction.response.defer()
        self.current_page -= 1

        data = self.data[self.current_page * self.separate:]
        await self.update(self.interaction, await self._create_embed(self.embed, data))

    @disnake.ui.button(label="▶️", style=disnake.ButtonStyle.blurple)
    async def next_page(
            self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ) -> None:
        await interaction.response.defer()
        self.current_page += 1

        data = self.data[self.current_page * self.separate:]
        await self.update(self.interaction, await self._create_embed(self.embed, data))

    async def interaction_check(self, interaction: MessageInteraction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.send(
                content="Sorry, you are not the interaction invoker!", ephemeral=True
            )
            return False
        return True


def custom_print(text: str, suffix: Literal["info", "starting", "warn", "error"] = "info", date: bool = True):
    suffixes = {
        "info": "\033[1;32;48mINFO\033[1;37;0m ",
        "starting": "\033[1;34;48mDEBUG\033[1;37;0m",
        "error": "\033[1;31;48mERROR\033[1;37;0m",
        "warn": "\033[1;33;48mWARN\033[1;37;0m "
    }

    print(f"{datetime.datetime.now().strftime('%H:%M:%S') if date else ''} {suffixes[suffix]}: {text}")
    return
