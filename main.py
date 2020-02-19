import discord
import logging
import sqlite3
import os
from discord.ext import commands

"""
Remember to finish your Heroku setup. You're on the git init part for the console.
https://www.youtube.com/watch?v=BPvg9bndP1U 8:35

#1 priority: figure out what sql database you're using - Heroku provides a postgre
database but also has extensions for things like MySql so look into that.
"""

DEFAULT_PREFIX = "."
TOKEN = os.environ['TOKEN']
DATABASE_PATH = 'D:/OneDrive/Documents/Discord Bots/Data Storage/Headmaster.db'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

"""
new_database = not os.path.exists(DATABASE_PATH)
connection = None
try:
    connection = sqlite3.connect()
except Exception as e:
    print(e)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

if new_database:
    pass
# TODO - Generate schema
"""


def get_prefix(client, message):
    return DEFAULT_PREFIX


client = commands.Bot(command_prefix=get_prefix, case_insensitive=True, help_command=None)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}. I am in {len(client.guilds)} guilds.")


@client.event
async def on_message(msg):
    await client.process_commands(msg)
    pass


# help is a default command - could be overridden if it looks ugly
@client.command(aliases=["help", "commands"])
async def _help(ctx):
    embed = discord.Embed(title="Headmaster - Commands", colour=discord.Colour(0x9e33f3),
                          description="*Custom bot of [**Roblox Development Academy**](https://discord.gg/Wxut87w)*\n*Dedicated to providing a perfect environment for teaching and learning.*")

    embed.set_footer(text="Made by JL for Roblox Development Academy",
                     icon_url="https://cdn.discordapp.com/avatars/260608867292020737/2d7b57f730ada4443b3921fbb75f324e.png?size=2048")

    embed.add_field(name="General Commands", value="**.help** - Shows this message\n**.ban** - Bans someone")

    await ctx.send(embed=embed)


client.run(TOKEN)
