import discord
import logging
import os
import psycopg2
from discord.ext import commands

"""
Looks like we're using Heroku's provided addon PostgresSQL: https://devcenter.heroku.com/articles/heroku-postgresql

Heroku also has addons for things like MySQL so check those out - but main concern is that Heroku might not be
as generous with speed or size as with its PostgresSQL database

Heroku also has support with its Postgres "heroku pg" commands

Too stingy with Postgres. Maybe look for different datastores. If there's no RAM... would it be slow?
Make a difference? Would I have to manually cache some data in dictionaries?
"""

DEFAULT_PREFIX = "."
TOKEN = os.environ['TOKEN']
DATABASE_URL = os.environ("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


connection = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = connection.cursor()


def generate_tables():
    print("Creating new tables")
    statements = {
        """
        CREATE TABLE IF NOT EXISTS guilds(
            
        )
        """
    }
# TODO - Generate schema


def get_prefix(client, message):
    return DEFAULT_PREFIX


client = commands.Bot(command_prefix=commands.when_mentioned_or(DEFAULT_PREFIX), case_insensitive=True, help_command=None)


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
