import database
import discord
from discord.ext import commands
from math import floor
from bot import lang
from yaml import load, FullLoader


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
        with open("config.yml") as f:
            categories = load(f, Loader=FullLoader)
            self.categories = categories['categories']

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if (reaction.emoji != lang.global_placeholders.get("emoji.solution")) or (
                reaction.message.author.id != user.id):
            return

        print(type(self.categories))

        category_name = None
        for category, channels in self.categories:
            if reaction.message.channel.id in channels:
                category_name = category
                break

        if category_name is None:
            return

        category_id, exp = database.query(
            """
            SELECT id, exp_rate
            FROM categories
            WHERE name = %s
            """,
            (category_name,)
        ).fetchone()

        Level.__add_exp(reaction.message.author.id, category_id, exp)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if (reaction.emoji != lang.global_placeholders.get("emoji.solution")) or (
                reaction.message.author.id != user.id):
            return

        category_name = None
        for category, channels in self.categories:
            if reaction.message.channel.id in channels:
                category_name = category
                break

        if category_name is None:
            return

        category_id, exp = database.query(
            """
            SELECT id, exp_rate
            FROM categories
            WHERE name = %s
            """,
            (category,)
        ).fetchone()

        Level.__add_exp(reaction.message.author.id, category_id, -exp)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        pass
