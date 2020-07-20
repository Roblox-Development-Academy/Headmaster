import database
import discord
from discord.ext import commands
from math import floor
from bot import lang, get_prefix
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


def add_exp(user_id, category_id, amount, multiplier_immune=False):
    if not multiplier_immune:
        pass
    database.update(
        """
        INSERT INTO levels (user_id, category_id, exp)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, category_id) DO
        UPDATE SET exp = exp + EXCLUDED.exp
        """,
        (user_id, category_id, amount)
    )
    total_exp = database.query(
                    """
                    SELECT exp
                    FROM levels
                    WHERE user_id = %s AND category_id = %s
                    """,
                    (user_id, category_id)
                ).fetchone()


class Level(commands.Cog):
    """
    Solution emote: Add exp.
    Profile emote: DM profile and remove reaction.
    Profile command: Show exp and level.
    Average 11 exp.
    """

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

        category_name = None
        for category in self.categories:
            if reaction.message.channel.id in self.categories[category]:
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

        add_exp(reaction.message.author.id, category_id, exp)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if (reaction.emoji != lang.global_placeholders.get("emoji.solution")) or (
                reaction.message.author.id != user.id):
            return

        category_name = None
        for category in self.categories:
            if reaction.message.channel.id in self.categories[category]:
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

        add_exp(reaction.message.author.id, category_id, -exp)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        pass

    @commands.command(aliases=("lb", "ranks", "ranking", "rankings", "levels", "leaderboards"))
    async def leaderboard(self, ctx, category=None):
        prefix = get_prefix(ctx.guild.id)
        if category:
            ranks = database.query(
                """
                SELECT user_id, exp
                FROM levels JOIN categories
                ON category_id = categories.id AND categories.name = %s
                ORDER BY exp DESC
                """,
                (category.capitalize(),)
            ).fetchall()

            if not ranks:
                await lang.get("error.invalid_category").send(ctx, category=category.capitalize(), prefix=prefix)
                return
            rank_strings = []
            for row in ranks:
                rank_strings.append(f"\\{self.client.get_user(row[0]).mention}\n**Level:** {calculate(row[1])}    Total Exp: {row[1]}")

            current_page = 1
            total_pages = floor(len(rank_strings)/10) + 1

            lb_message = await lang.get("leaderboard.category").send(ctx, category=category.capitalize(), leaderboard='\n\n'.join(rank_strings[(current_page - 1) * 10:current_page * 2]), page=f"{current_page}/{total_pages}")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in (lang.global_placeholders.get("emoji.next"), lang.global_placeholders.get("emoji.previous")) and reaction.message ==  lb_message
            while True:
                try:
                    reaction, user = await self.client.wait_for('reaction_add', timeout=251, check=check)
                    if reaction == lang.global_placeholders.get("emoji.next"):
                        current_page += 1
                    else:
                        current_page -= 1
                    await lang.get("leaderboard.category").edit(ctx, category=category.capitalize(), leaderboard='\n\n'.join(rank_strings[(current_page - 1) * 10:current_page * 2]), page=f"{current_page}/{total_pages}")
                except TimeoutError:
                    inactive_embed = lb_message.embeds[0]
                    inactive_embed.color = lang.global_placeholders.get("color.inactive")
                    await lb_message.edit("This message is inactive. Please execute the command again to interact.", embed=inactive_embed)
                    break
        else:
            await lang.get("leaderboard.main").send(ctx, prefix=prefix)

    @commands.command()
    async def categories(self, ctx):
        rows = database.query(
            """
            SELECT name, exp_rate
            FROM categories
            """
        ).fetchall()

