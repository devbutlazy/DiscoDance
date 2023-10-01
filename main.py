import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction
from nextcord.abc import GuildChannel
import nextcord.utils
from nextcord.ext.commands import cooldown, BucketType
from nextcord.errors import Forbidden
from nextcord.ui import Button, View, Modal, TextInput
from nextcord.ext.commands import (CommandNotFound, BadArgument, MissingRequiredArgument, MissingPermissions, CommandOnCooldown)
import pyshorteners
import asyncio, datetime, os, io, contextlib
import random
import urllib
import json
import sqlite3
from requests import get
import aiohttp
from wavelink.ext import spotify
import wavelink
import aiosqlite
from io import BytesIO
import psutil
import datetime
import time
from nextcord import Interaction, SlashOption, ChannelType
from nextcord.ext import application_checks
from asyncio import sleep
from itertools import cycle
import string
from nextcord.utils import format_dt



bot = commands.Bot(command_prefix=">", strip_after_prefix=True, intents=nextcord.Intents.all())


class queueView(View):
    @nextcord.ui.button(label="Skip", style=nextcord.ButtonStyle.green)
    async def skips(self, button, interaction: nextcord.Interaction):
        if interaction.guild.voice_client.queue.is_empty:
            return await interaction.response.send_message(
                "Queue is empty, write `>play` to play some music or I will disconnect at the end of the music!",
                ephemeral=True)

        try:
            next_song = interaction.guild.voice_client.queue.get()
            await interaction.guild.voice_client.play(next_song)
            embed = nextcord.Embed(title=f"Music from - {interaction.guild.voice_client.track.author} ",
                                   description=f"[{interaction.guild.voice_client.track.title}]({str(interaction.guild.voice_client.track.uri)})",
                                   color=0x2F3136)
            embed.add_field(name="Artist:", value=f"**`{interaction.guild.voice_client.track.author}`**", inline=True)
            embed.add_field(name="Duration:",
                            value=f"**`{str(datetime.timedelta(seconds=interaction.guild.voice_client.track.length))}`**",
                            inline=True)
            embed.set_footer(text=f"Music by Que")
            embed.set_image(url=f"{interaction.guild.voice_client.track.thumbnail}")
            await interaction.message.edit(embed=embed, view=queueView())
        except Exception:
            return await interaction.response.send_message(
                "Queue empty, write `>play` to play some music or I will disconnect at the end of the music!",
                ephemeral=True)

    @nextcord.ui.button(label="Resume/Pause", style=nextcord.ButtonStyle.blurple)
    async def resume_and_pause(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if interaction.guild.voice_client.is_paused():
            await interaction.guild.voice_client.resume()
        else:
            await interaction.guild.voice_client.pause()

    @nextcord.ui.button(label="Disconnect", style=nextcord.ButtonStyle.danger)
    async def dc(self, button, interaction):
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(
            embed=nextcord.Embed(title="Dissconect", description="I have disconnected", color=0x2F3136))


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    await bot.change_presence(activity=nextcord.Game(name=f">play <music>"))
    bot.loop.create_task(node_connect())


async def node_connect():
    await bot.wait_until_ready()
    await wavelink.NodePool.create_node(bot=bot, host='lava.link', port=80, password='dismusic', spotify_client=spotify.SpotifyClient(client_id="35e4a1289f4745f494aa9e6c418c9a0a", client_secret="2fe747df85f34bbdb23557e7ce31dc9b"))

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f"Node {node.identifier} ready!")

@bot.command()
async def loop(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send("You are not playing any music")
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("You have to be in voice channel!")
    else:
        vc: wavelink.Player = ctx.voice_client

    try:
        vc.loop = True
    except:
        setattr(vc, "loop", False)

    if vc.loop:
        return await ctx.send("Loop is now enable")
    else:
        return await ctx.send("Loop is now disabled")

@bot.event
async def on_wavelink_track_end(player: wavelink.Player, track: wavelink.Track, reason):
    if player.loop:
        return await player.play(track)

    if reason == "FINISHED":
        try:
            next_song = player.queue.get()
            return await player.play(next_song)
        except wavelink.QueueEmpty:
            await player.disconnect(force=True)

@bot.slash_command(description="Plays youtube music")
async def play(interaction: Interaction, channel: GuildChannel = SlashOption(channel_types=[ChannelType.voice],
                                                                             description="Voice channel to join"),
               search: str = SlashOption(description="Song Name")):
    search = await wavelink.YouTubeTrack.search(query=search, return_first=True)
    if not interaction.guild.voice_client:
        vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
    elif not getattr(interaction.user.voice, "channel", None):
        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        return await interaction.send(embed=embed, view=queueView())
    else:
        vc: wavelink.Player = interaction.guild.voice_client

    if vc.queue.is_empty and not vc.is_playing():
        await vc.play(search)
        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        await interaction.send(embed=embed, view=queueView())
    else:
        await vc.queue.put_wait(search)
        await interaction.send(
            embed=nextcord.Embed(title="Queue", description=f"{search.title} added to the queue!", color=0x2F3136))
    vc.interaction = interaction
    try:
        if vc.loop: return
    except Exception:
        setattr(vc, "loop", False)

@bot.slash_command(description="Shows the music queue")
async def queue(interaction: Interaction):
    if not interaction.guild.voice_client:
        vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
    elif not getattr(interaction.user.voice, "channel", None):
        return await interaction.send("Join the voice channel first.")
    else:
        vc: wavelink.Player = interaction.guild.voice_client

        if not vc.is_playing():
            embed = nextcord.Embed(title="Music", description="Man, nothing is playing yet ....", color=0x2F3136)
            embed.set_footer(text="Man, why can't people be a little smarter?")
            await interaction.send(embed=embed)

        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        await interaction.send(embed=embed, view=queueView())

@bot.slash_command(name="volume", description="Sets the music volume")
async def volume(interaction: Interaction, volume: int):
    if not interaction.guild.voice_client:
        return await interaction.send(
            embed=nextcord.Embed(title="I'm not even in the voice channel!", color=nextcord.Color.red()))
    elif not getattr(interaction.user.voice, "channel", None):
        return await interaction.send(
            embed=nextcord.Embed(title="Join the channel first, lol", color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = interaction.guild.voice_client

    if volume > 100:
        return await interaction.send(embed=nextcord.Embed(title="It's to big! .-.", color=nextcord.Color.red()))
    elif volume < 0:
        return await interaction.send(embed=nextcord.Embed(title="It's to small! ._.", color=nextcord.Color.red()))
    await interaction.send(embed=nextcord.Embed(title="Success",
                                                description=f" <:yes:993171492563079260>    |   I have successfuly set the volume to `{volume}`%",
                                                color=0x2F3136))
    return await vc.set_volume(volume)

@bot.command()
async def play(ctx: commands.Context, *, search: wavelink.YouTubeTrack):
    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("Join a voice channel first, lol")
    else:
        vc: wavelink.Player = ctx.voice_client

    if vc.queue.is_empty and not vc.is_playing():
        await vc.play(search)
        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        await ctx.send(embed=embed, view=queueView())
    else:
        await vc.queue.put_wait(search)
        await ctx.send(
            embed=nextcord.Embed(title="Queue", description=f"{search.title} added to the queue!", color=0x2F3136))
    vc.ctx = ctx
    try:
        if vc.loop: return
    except Exception:
        setattr(vc, "loop", False)

@bot.command()
async def queue(ctx):
    if not ctx.voice_client:
        vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("Join the voice channel first.")
    else:
        vc: wavelink.Player = ctx.voice_client

        if not vc.is_playing():
            embed = nextcord.Embed(title="Music", description="Man, nothing is playing yet ....", color=0x2F3136)
            embed.set_footer(text="Man, why can't people be a little smarter?")
            await ctx.send(embed=embed)

        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        await ctx.send(embed=embed, view=queueView())

@bot.command(aliases=["volume"])
async def volume(ctx, volume: int):
    if not ctx.voice_client:
        return await ctx.send(
            embed=nextcord.Embed(title="I'm not even in the voice channel!", color=nextcord.Color.red()))
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(embed=nextcord.Embed(title="Join the channel first, lol", color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = ctx.voice_client

    if volume > 100:
        return await ctx.send(embed=nextcord.Embed(title="It's to big! .-.", color=nextcord.Color.red()))
    elif volume < 0:
        return await ctx.send(embed=nextcord.Embed(title="It's to small! ._.", color=nextcord.Color.red()))
    await ctx.send(embed=nextcord.Embed(title="Success",
                                        description=f" <:yes:993171492563079260>    |   I have successfuly set the volume to `{volume}`%",
                                        color=0x2F3136))
    return await vc.set_volume(volume)

@bot.command()
async def pause(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send(embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                                   color=nextcord.Color.red()))
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
        return await ctx.send(embed=nextcord.Embed(title="<:no:993171433981227058> | Play some music first, lol",
                                                   color=nextcord.Color.red()))

    await vc.pause()
    await ctx.send(embed=nextcord.Embed(title="<:yes:993171492563079260> | Music is now paused", color=0x2F3136),
                   view=queueView())

@bot.command()
async def resume(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send(embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                                   color=nextcord.Color.red()))
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = ctx.voice_client
    if vc.is_playing():
        return await ctx.send(embed=nextcord.Embed(title="<:no:993171433981227058> | Music is already playing, lol",
                                                   color=nextcord.Color.red()))

    await vc.resume()
    return await ctx.send(
        embed=nextcord.Embed(title="<:yes:993171492563079260> | Music is now resumed", color=0x2F3136),
        view=queueView())

@bot.command()
async def skip(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send(embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                                   color=nextcord.Color.red()))
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = ctx.voice_client
    if not vc.is_playing():
        return await ctx.send(embed=nextcord.Embed(title="<:no:993171433981227058> | Play some music first, lol",
                                                   color=nextcord.Color.red()))

    try:
        next_song = vc.queue.get()
        await vc.play(next_song)
        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        await ctx.send(embed=embed, view=queueView())
    except Exception:
        return await ctx.send(embed=nextcord.Embed(
            title="<:no:993171433981227058> | Que is empty. Play some music, or I'll leave when this song ends.",
            color=nextcord.Color.red()))

    await vc.stop()

@bot.command()
async def disconnect(ctx: commands.Context):
    if not ctx.voice_client:
        return await ctx.send(embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                                   color=nextcord.Color.red()))
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = ctx.voice_client

    await vc.disconnect()
    return await ctx.send(
        embed=nextcord.Embed(title="<:yes:993171492563079260> | I have left teh channel.", color=0x2F3136))

@bot.slash_command(description="Pauses music")
async def pause(interaction: Interaction):
    if not interaction.guild.voice_client:
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                 color=nextcord.Color.red()))
    elif not getattr(interaction.user.voice, "channel", None):
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = interaction.guild.voice_client
    if not vc.is_playing():
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Play some music first, lol",
                                 color=nextcord.Color.red()))

    await vc.pause()
    await interaction.send(
        embed=nextcord.Embed(title="<:yes:993171492563079260> | Music is now paused", color=0x2F3136),
        view=queueView())

@bot.slash_command(description="Resumes music")
async def resume(interaction: Interaction):
    if not interaction.guild.voice_client:
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                 color=nextcord.Color.red()))
    elif not getattr(interaction.user.voice, "channel", None):
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = interaction.guild.voice_client
    if vc.is_playing():
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Music is already playing, lol",
                                 color=nextcord.Color.red()))

    await vc.resume()
    return await interaction.send(
        embed=nextcord.Embed(title="<:yes:993171492563079260> | Music is now resumed", color=0x2F3136),
        view=queueView())

@bot.slash_command(description="Skips music")
async def skip(interaction: Interaction):
    if not interaction.guild.voice_client:
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                 color=nextcord.Color.red()))
    elif not getattr(interaction.user.voice, "channel", None):
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = interaction.guild.voice_client
    if not vc.is_playing():
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Play some music first, lol",
                                 color=nextcord.Color.red()))

    try:
        next_song = vc.queue.get()
        await vc.play(next_song)
        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        await interaction.send(embed=embed, view=queueView())
    except Exception:
        return await interaction.send(embed=nextcord.Embed(
            title="<:no:993171433981227058> | Que is empty. Play some music, or I'll leave when this song ends.",
            color=nextcord.Color.red()))

    await vc.stop()

@bot.slash_command(description="Disconnects from a vc")
async def disconnect(interaction: Interaction):
    if not interaction.guild.voice_client:
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | I'm not even in vc, lol",
                                 color=nextcord.Color.red()))
    elif not getattr(interaction.user.voice, "channel", None):
        return await interaction.send(
            embed=nextcord.Embed(title="<:no:993171433981227058> | Join a voice channel first, lol",
                                 color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = interaction.guild.voice_client

    await vc.disconnect()
    return await interaction.send(
        embed=nextcord.Embed(title="<:yes:993171492563079260> | I have left teh channel.", color=0x2F3136))


@bot.slash_command(description="Plays spotify music")
async def splay(interaction: Interaction, channel: GuildChannel = SlashOption(channel_types=[ChannelType.voice],
                                                                              description="Voice channel to join"),
                search: str = SlashOption(description="Song Name")):
    if not interaction.guild.voice_client:
        vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
    elif not getattr(interaction.user.voice, "channel", None):
        embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                               description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
        embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
        embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                        inline=True)
        embed.set_footer(text=f"Music by Que")
        embed.set_image(url=f"{vc.track.thumbnail}")
        return await interaction.send(embed=embed, view=queueView())
    else:
        vc: wavelink.Player = interaction.guild.voice_client

    if vc.queue.is_empty and not vc.is_playing():
        try:
            track = await spotify.SpotifyTrack.search(query=search, return_first=True)
            await vc.play(track)
            embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                                   description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
            embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
            embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                            inline=True)
            embed.set_footer(text=f"Music by Que")
            embed.set_image(url=f"{vc.track.thumbnail}")
            await interaction.send(embed=embed, view=queueView())
        except Exception as e:
            await interaction.send(embed=nextcord.Embed(title="Error",
                                                        description="<:no:993171433981227058> | Please enter a spotify, son **url**",
                                                        color=nextcord.Color.red()))
    else:
        await vc.queue.put_wait(search)
        await interaction.send(embed=nextcord.Embed(title="Queue", description=f"Added to the queue!", color=0x2F3136))
        vc.interaction = interaction
    try:
        if vc.loop: return
    except Exception:
        setattr(vc, "loop", False)


@bot.command()
async def splay(ctx: commands.Context, *, search: str):
    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send(embed=nextcord.Embed(title="Error",
                                                   description="<:no:993171433981227058> | Join a voice channel first, lol 🤣😂",
                                                   color=nextcord.Color.red()))
    else:
        vc: wavelink.Player = ctx.voice_client

    if vc.queue.is_empty and not vc.is_playing():
        try:
            track = await spotify.SpotifyTrack.search(query=search, return_first=True)
            await vc.play(track)
            embed = nextcord.Embed(title=f"Music from - {vc.track.author} ",
                                   description=f"[{vc.track.title}]({str(vc.track.uri)})", color=0x2F3136)
            embed.add_field(name="Artist:", value=f"**`{vc.track.author}`**", inline=True)
            embed.add_field(name="Duration:", value=f"**`{str(datetime.timedelta(seconds=vc.track.length))}`**",
                            inline=True)
            embed.set_footer(text=f"Music by Que")
            embed.set_image(url=f"{vc.track.thumbnail}")
            await ctx.send(embed=embed, view=queueView())
        except Exception as e:
            await ctx.send(embed=nextcord.Embed(title="Error",
                                                description="<:no:993171433981227058> | Please enter a spotify, son **url**",
                                                color=nextcord.Color.red()))
    else:
        await vc.queue.put_wait(search)
        await ctx.send(embed=nextcord.Embed(title="Queue", description=f"Added to the queue!", color=0x2F3136))
    vc.ctx = ctx
    try:
        if vc.loop: return
    except Exception:
        setattr(vc, "loop", False)


bot.run("MTA3OTAzMTI3MzY5MzEzOTAxNA.Gk_Obz.n37oA5vHSL2YdQb-01scTvGa0lms9g50mmjoV4")
