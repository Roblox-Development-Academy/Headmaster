import database
import discord
from psycopg2 import DatabaseError
from discord.ext import commands
import math


def calculate(exp):
    exp_left = exp
    level = -1
    while exp_left >= 0:
        level += 1
        exp_left = exp_left  # - number.
    return level


def __add_exp(user_id, category_id, amount):
    try:
        database.cursor.executemany(
            """
            INSERT INTO levels (user_id, category_id, exp)
            VALUES (%s, %s, %s + exp)
            ON CONFLICT (user_id, category_id) DO NOTHING
            """,
            (user_id, category_id, amount)
        )
        database.connection.commit()
    except DatabaseError:
        database.connect()
        __add_exp(user_id, category_id, amount)


class Level(commands.Cog):
    """
    Solution emote: Add exp.
    Profile emote: DM profile and remove reaction.
    Profile command: Show exp and level.
    Average 10 exp.
    """
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        print(payload.emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        print(payload.emoji)

    @commands.command()
    @commands.guild_only()
    async def profile(self, ctx, member: discord.Member = None):
        ...
