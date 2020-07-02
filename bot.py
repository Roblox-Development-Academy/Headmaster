import os as __os
import logging as __logging

import discord
from discord.ext import commands

import database
from language import LangManager as __LangManager

TOKEN = __os.environ['TOKEN']
JANITOR_TOKEN = __os.environ['JANITOR_TOKEN']
EMBED_COLORS = {
    'info': discord.Colour(0x9e33f3),
    'error': discord.Colour(0xf62323),
    'success': discord.Colour(0x5efb32),
    'wizard': discord.Colour(0x00f6ff)
}
EMOJIS = {
    'confirm': ":white_check_mark:",
    'gotcha': ":thumbs_up:",
    'error': ":crying_cat_face:",
    'date': ":calendar:",
    'time': ":timer:"
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

rda = client.get_guild(673600024919408680)

in_prompt = {}

lang = __LangManager('messages.yml', bot=client)
