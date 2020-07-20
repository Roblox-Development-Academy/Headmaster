import database
import discord
from discord.ext import commands
from math import floor
from bot import lang


def calculate(exp, is_profile=False):
    level_exp = 121
    exp_left = exp
    remainder = exp_left
    level = -1
    while exp_left >= 0:
        level_exp = 121 * (floor(level / 11) + 1) + (1331 if level >= 121 else 0)
        remainder = exp_left
        level += 1
        exp_left = exp_left - level_exp
    if is_profile:
        return level, remainder, level_exp
    return level


class Level(commands.Cog):
    """
    Solution emote: Add exp.
    Profile emote: DM profile and remove reaction.
    Profile command: Show exp and level.
    Average 11 exp.
    """

    @staticmethod
    def __add_exp(user_id, category_id, amount):
        database.update(
            """
            INSERT INTO levels (user_id, category_id, exp)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, category_id) DO
            UPDATE SET exp = exp + EXCLUDED.exp
            """,
            (user_id, category_id, amount)
        )

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji != lang.global_placeholders.get("emoji.solution"):
            return
        category = None

        category_id, exp = database.query(
            """
            SELECT id, exp_rate
            FROM categories
            WHERE name = %s
            """,
            (category,)
        ).fetchone()

        receiver_id = reaction.message.author.id

        if receiver_id != user.id:
            Level.__add_exp(receiver_id, category_id, exp)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if reaction.emoji != lang.global_placeholders.get("emoji.solution"):
            return
        pass
        category = None

        category_id, exp = database.query(
            """
            SELECT id, exp_rate
            FROM categories
            WHERE name = %s
            """,
            (category,)
        ).fetchone()

        receiver_id = reaction.message.author.id

        if receiver_id != user.id:
            Level.__add_exp(receiver_id, category_id, -exp)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        pass
