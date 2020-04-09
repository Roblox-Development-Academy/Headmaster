import os
import logging

import discord
from discord.ext import commands

import database

DEFAULT_PREFIX = "."
TOKEN = os.environ['TOKEN']
JANITOR_TOKEN = os.environ['JANITOR_TOKEN']
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
__handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
__handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
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
    return DEFAULT_PREFIX if row is None else row[0]


def get_mention_or_prefix(bot, message):
    if not message.guild:  # Sent in DMs
        return DEFAULT_PREFIX

    return commands.when_mentioned_or(get_prefix(message.guild.id))(client, message)


client = commands.Bot(command_prefix=get_mention_or_prefix, case_insensitive=True, help_command=None)

janitor = discord.Client()
