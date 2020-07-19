import database
import discord
from discord.ext import commands


def calculate(exp):
    exp_left = exp
    level = -1
    while exp_left >= 0:
        level += 1
        exp_left = exp_left  # - number.
    return level


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
