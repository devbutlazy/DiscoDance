import datetime

import disnake
import mafic
from disnake.ext import commands
from disnake.ui import View

from utils import EmbedPaginator


class MusicPlayer(mafic.Player[commands.Bot]):
    def __init__(
            self,
            client: commands.Bot,
            channel: disnake.VoiceChannel,
    ) -> None:
        super().__init__(client, channel)

        self.queue: list[mafic.Track] = []
        self.voice_channel: disnake.VoiceChannel = channel


class QueueView(View):
    def __init__(self, bot: commands.bot, message_id: int, *, timeout: float | None = None) -> None:
        self.message_id = message_id
        self.bot = bot
        super().__init__(timeout=timeout)

    @disnake.ui.button(label="Skip", style=disnake.ButtonStyle.green, row=0)
    async def skip(
            self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ) -> None:
        player: MusicPlayer

        if player := interaction.guild.voice_client:  # type: ignore
            if not player.queue:
                return await interaction.response.send_message(
                    "Sorry, the music queue is empty!",
                    ephemeral=True,
                )

            try:
                await player.stop()
                message = await interaction.channel.fetch_message(self.message_id)
                await message.delete()
                await interaction.response.defer()

            except (mafic.PlayerNotConnected, disnake.Forbidden):
                return await interaction.send(
                    "Sorry, there was an error while processing your request.",
                    ephemeral=True,
                )

    @disnake.ui.button(label="Resume/Pause", style=disnake.ButtonStyle.gray, row=0)
    async def resume_and_pause(
            self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        player: MusicPlayer

        if player := interaction.guild.voice_client:  # type: ignore
            if player.paused:
                await player.resume()
                await interaction.response.edit_message(content=f"")
            else:
                await player.pause()
                await interaction.response.edit_message(content=f"")

    @disnake.ui.button(label="Volume", style=disnake.ButtonStyle.green, row=0)
    async def _volume(self, _: disnake.ui.Button, interaction: disnake.MessageInteraction):
        player: MusicPlayer

        if player := interaction.guild.voice_client:  # type: ignore
            modal = disnake.ui.Modal(
                title="Enter the volume",
                custom_id="volume",
                components=[
                    disnake.ui.TextInput(
                        label="New volume:",
                        custom_id="new_volume",
                        style=disnake.TextInputStyle.short,
                    )
                ],
            )
            await interaction.response.send_modal(modal=modal)
            response_modal = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "volume" and i.user == interaction.user,
            )
            new_volume = int(response_modal.text_values["new_volume"])
            try:
                await player.set_volume(new_volume)
                embed = disnake.Embed(
                    title=f"Set volume to {new_volume}",
                    color=disnake.Color.green()
                )
                await response_modal.response.send_message(embed=embed, ephemeral=True)
            except (Exception, BaseException, disnake.Forbidden):
                embed = disnake.Embed(
                    color=disnake.Color.red()
                )
                if new_volume > 100 or new_volume < 1:
                    embed.title = f"Please enter a number, between `1` and `100`"
                else:
                    embed.title = f"Sorry, something went wrong"

                await response_modal.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="Queue", style=disnake.ButtonStyle.blurple, row=1)
    async def queue(
            self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        player: MusicPlayer

        if player := interaction.guild.voice_client:  # type: ignore
            embed = disnake.Embed(
                title="Music Queue",
                description="",
                color=0x2F3236,
            )

            if len(player.queue) > 0:
                for index, music in enumerate(player.queue, start=1):
                    if index > 10:
                        break

                    embed.description += (
                        f"`{index}.` **{music.author} - {music.title}**\n"
                    )

                embed.set_footer(text="Page 1")

                paginator = EmbedPaginator(
                    interaction, interaction.user, embed, player.queue[10:], None, 10
                )
                return await paginator.send_message(interaction)
            else:
                embed.description = "No music in the queue\n"

            embed.set_footer(text="https://github.com/devbutlazy/DiscoDance")

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @disnake.ui.button(label="Disconnect", style=disnake.ButtonStyle.danger, row=1)
    async def dc(self, _: disnake.ui.Button, interaction: disnake.MessageInteraction):
        player: MusicPlayer

        if player := interaction.guild.voice_client:  # type: ignore
            await player.disconnect()
            await interaction.response.send_message(
                embed=disnake.Embed(
                    title="Disconnecting...",
                    description="I have disconnected from voice channel",
                    color=0x2F3236,
                ),
                ephemeral=True,
            )


class MusicPlatform(disnake.ui.Select):
    def __init__(self, bot: commands.bot) -> None:
        self.bot = bot

        options = [
            disnake.SelectOption(label="Youtube", description="Youtube music"),
            disnake.SelectOption(label="Spotify", description="Spotify music")
        ]
        super().__init__(
            placeholder="Choose a music platform",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="music_platform"
        )

    async def callback(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer()


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super(Music, self).__init__()
        self.bot = bot
        self.pool = mafic.NodePool(self.bot)
        self.bot.loop.create_task(self.add_nodes())

    async def add_nodes(self):
        await self.pool.create_node(
            label="MAIN",
            host="localhost",
            port=2333,
            password="youshallnotpass",
        )

    @commands.command()
    async def play(self, ctx: commands.Context, *, query: str = None):
        ErrorEmbed = disnake.Embed(color=disnake.Color.red())
        if not query:
            ErrorEmbed.title = "Please provide a query/URL to search"
            return await ctx.send(embed=ErrorEmbed)

        if not getattr(ctx.author.voice, "channel", None):
            ErrorEmbed.title = "Join a voice channel first"
            return await ctx.send(embed=ErrorEmbed)

        voice = ctx.author.voice.channel

        player: MusicPlayer = ctx.guild.voice_client or await voice.connect(
            cls=MusicPlayer  # type: ignore
        )

        select = MusicPlatform(self.bot)
        view = disnake.ui.View().add_item(select)
        await ctx.channel.send("Choose a music platform:", view=view)
        await self.bot.wait_for(
            "dropdown",
            check=lambda i: i.component.custom_id == "music_platform" and i.user == ctx.author,
        )

        selected_platform = select.values[0]
        if selected_platform == "Spotify":
            embed = disnake.Embed(
                title="Spotify Music",
                color=disnake.Color.green()
            )
            await ctx.send(embed=embed)
            tracks = await player.fetch_tracks(query, search_type="spsearch")
        elif selected_platform == "Youtube":
            embed = disnake.Embed(
                title="Youtube Music",
                color=disnake.Color.red()
            )
            await ctx.send(embed=embed)
            tracks = await player.fetch_tracks(query)
        else:
            embed = disnake.Embed(
                title="Invalid music platform selected",
                color=disnake.Color.red()
            )
            return await ctx.send(embed=embed)

        if not tracks:
            ErrorEmbed.title = f"No tracks found, by `{query}` query..."
            return await ctx.send(embed=ErrorEmbed)

        embed = disnake.Embed(color=0x2F3236)

        if ctx.channel is not voice:
            await ctx.channel.send(f"{ctx.author.mention} Please check your voice channel messages", delete_after=15)
        if player.current:
            embed.title = "Queue"

            if isinstance(tracks, mafic.Playlist):
                player.queue.extend(tracks.tracks)
                embed.description = f"Added playlist **{tracks.name}** ({len(tracks.tracks)} tracks) to the queue."
            else:
                player.queue.append(tracks[0])
                embed.description = f"Added track **[{tracks[0].title}]({str(tracks[0].uri)})** to the queue."
                embed.add_field(
                    name="Artist:", value=f"**`{tracks[0].author}`**", inline=True
                )
                embed.add_field(
                    name="Duration:",
                    value=f"`{str(datetime.timedelta(seconds=round(tracks[0].length / 1000)))}`",
                    inline=True,
                )
                embed.add_field(
                    name="Message deletion in:",
                    value=f"**`15 seconds`**",
                    inline=True,
                )
                embed.set_image(url=tracks[0].artwork_url)

            embed.set_footer(text="https://github.com/devbutlazy/DiscoDance")
            message = await voice.send(embed=embed, delete_after=15)
            await message.edit(embed=embed, delete_after=15, view=QueueView(self.bot, message.id))

        else:
            if isinstance(tracks, mafic.Playlist):
                player.queue.extend(tracks.tracks[1:])
                await player.play(tracks.tracks[0])

                embed.title = f"Now playing - {tracks.tracks[0].title}"
                embed.description = (
                    f"[{tracks.tracks[0].title}]({str(tracks.tracks[0].uri)})"
                    f"\nAdded playlist {tracks.name} ({len(tracks.tracks) - 1} tracks) to the queue."
                )
                embed.add_field(
                    name="Artist:",
                    value=f"**`{tracks.tracks[0].author}`**",
                    inline=True,
                )
                embed.add_field(
                    name="Duration:",
                    value=f"`{str(datetime.timedelta(seconds=round(tracks.tracks[0].length / 1000)))}`",
                    inline=True,
                )
                embed.set_image(url=tracks.tracks[0].artwork_url)

                message = await voice.send(embed=embed)
                return await message.edit(embed=embed, view=QueueView(self.bot, message.id))
            else:
                await player.play(tracks[0])

                embed.title = f"Now playing - {tracks[0].title}"
                embed.description = f"[{tracks[0].title}]({str(tracks[0].uri)})"
                embed.add_field(
                    name="Artist:", value=f"**`{tracks[0].author}`**", inline=True
                )
                embed.add_field(
                    name="Duration:",
                    value=f"`{str(datetime.timedelta(seconds=round(tracks[0].length / 1000)))}`",
                    inline=True,
                )
                embed.set_image(url=tracks[0].artwork_url)

                embed.set_footer(text="https://github.com/devbutlazy/DiscoDance")

            message = await voice.send(embed=embed)
            await message.edit(embed=embed, view=QueueView(self.bot, message.id))

    @commands.Cog.listener()
    async def on_track_end(self, event: mafic.TrackEndEvent[MusicPlayer]):
        if event.player.queue:
            track = event.player.queue.pop(0)
            await event.player.play(track)

            embed = disnake.Embed(
                title=f"Now playing - {track.title}",
                description=f"[{track.title}]({str(track.uri)})",
                color=0x2F3236,
            )
            embed.add_field(name="Artist:", value=f"**`{track.author}`**", inline=True)
            embed.add_field(
                name="Duration:",
                value=f"`{str(datetime.timedelta(seconds=round(track.length / 1000)))}`",
                inline=True,
            )
            embed.set_footer(text="https://github.com/devbutlazy/DiscoDance")
            embed.set_image(url=track.artwork_url)

            message = await event.player.voice_channel.send(embed=embed)

            return await message.edit(
                embed=embed, view=QueueView(self.bot, message_id=message.id)
            )
        else:
            return await event.player.disconnect(force=True)

    @commands.Cog.listener()
    async def on_track_start(self, event: mafic.TrackStartEvent) -> None:
        assert isinstance(event.player, MusicPlayer)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Music(bot))
