import os as __os
import logging as __logging
import asyncio as __asyncio

import discord
from discord.ext import commands

import database
from language import LangManager as __LangManager

from yaml import load, FullLoader

TOKEN = __os.environ['TOKEN']
WEB_URL = __os.environ['URL']

__logging.basicConfig(level=__logging.INFO)
logger = __logging.getLogger('discord')
logger.setLevel(__logging.INFO)
__handler = __logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
__handler.setFormatter(__logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(__handler)


def get_ignored_channels(guild_id):
    return database.query(
        """
        SELECT id
        FROM ignored_channels
        WHERE guild_id = %s
        """,
        (guild_id,)
    ).fetchall()


def get_prefix(guild_id):
    row = database.query(
        """
        SELECT prefix
        FROM guilds
        WHERE guilds.id = %s
        """,
        (guild_id,)
    ).fetchone()
    return lang.global_placeholders.get('default_prefix') if row is None else row[0]


def get_mention_or_prefix(_, message):
    if not message.guild:  # Sent in DMs
        return commands.when_mentioned_or(lang.global_placeholders.get('default_prefix'))(client, message)

    return commands.when_mentioned_or(get_prefix(message.guild.id))(client, message)


client = commands.Bot(command_prefix=get_mention_or_prefix, case_insensitive=True, help_command=None)


rda: discord.Guild
class_channel: discord.TextChannel
class_category: discord.CategoryChannel
teacher_role: discord.Role

__loop = __asyncio.get_event_loop()
__loop.create_task(client.start(TOKEN))


@client.listen('on_ready')
async def __on_ready():
    global rda, class_channel, class_category, teacher_role
    if __os.environ['DEBUG'] == 1:
        rda = client.get_guild(676175299121250327)
        class_channel = rda.get_channel(739213440803012608)
        class_category = rda.get_channel(677766311530594305)
        teacher_role = rda.get_role(677766292714815508)
        logger.info("Created globals using DEBUG set")
    else:
        rda = client.get_guild(673600024919408680)
        class_channel = rda.get_channel(673604720601858069)
        class_category = rda.get_channel(673604345316638730)
        teacher_role = rda.get_role(673608309198028811)
        logger.info("Created globals using production set")
    logger.info(f"Logged in as {client.user}. I am in {len(client.guilds)} guilds.")

in_prompt = {}  # Dict of user IDs to their prompt message URLs; users in the middle of a prompt can't run commands

lang = __LangManager('messages.yml')

with open("config.yml") as f:
    config = load(f, Loader=FullLoader)
    if __os.environ['DEBUG'] == '1':
        __test = 'test_'
    elif __os.environ['DEBUG'] == '0':
        __test = ''

    servers = config[__test + 'servers']
    channels = config[__test + 'channels']
    categories = config[__test + 'categories']
