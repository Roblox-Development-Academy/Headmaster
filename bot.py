import os as __os
import logging as __logging

import discord
from discord.ext import commands

import database
from language import LangManager as __LangManager

from yaml import load, FullLoader

TOKEN = __os.environ['TOKEN']
JANITOR_TOKEN = __os.environ['JANITOR_TOKEN']
EMBED_COLORS = {
    'info': discord.Colour(0x9e33f3),
    'error': discord.Colour(0xf62323),
    'success': discord.Colour(0x5efb32),
    'wizard': discord.Colour(0x00f6ff)
}
EMOJIS = {
    'confirm': "\U00002705",  # :white_check_mark:
    'gotcha': "\U0001f44d",  # :thumbs_up:
    'error': "\U0001f63f",  # :crying_cat_face:
    'date': "\U0001f4c6",  # :calendar:
    'time': "\U000023f2"  # :timer:
}

__logging.basicConfig(level=__logging.INFO)
logger = __logging.getLogger('discord')
logger.setLevel(__logging.DEBUG)
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

janitor = discord.Client()

in_prompt = {}

lang = __LangManager('messages.yml', bot=client)

with open("config.yml") as f:
    config = load(f, Loader=FullLoader)
    if __os.environ['DEBUG'] == '1':
        __test = 'test_'
    elif __os.environ['DEBUG'] == '0':
        __test = ''

    servers = config[__test + 'servers']
    channels = config[__test + 'channels']
    categories = config[__test + 'categories']

rda = client.get_guild(servers['rda'])
