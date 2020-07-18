import database
import discord
from psycopg2 import DatabaseError
from discord.ext import commands


def __add_exp(user_id, category_id, amount: int):
    ...


class Level(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        ...

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        ...

    @commands.command()
    @commands.guild_only()
    async def level(self, ctx, member: discord.Member = None):
        ...
