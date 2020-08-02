import database
import conditions

from discord import Member, User
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from math import floor, ceil, fabs
from bot import lang, get_prefix
from yaml import load, FullLoader
from copy import deepcopy
from psycopg2 import DatabaseError
from common import parse_interval
from bot import client


def calculate_level(exp, is_profile=False):
    level_exp = 121
    exp_left = exp
    remainder = exp_left
    level = -1
    while exp_left >= 0:
        level += 1
        level_exp = 121 * (floor(level / 11) + 1)

        if level >= 51:
            level_exp += 1331
            if level >= 121:
                level_exp += 14641
                if level >= 142:
                    level_exp += 161051

        remainder = exp_left
        exp_left = exp_left - level_exp
    if is_profile:
        return level, remainder, level_exp
    return level


async def add_exp(user_id, category_name, amount, multiplier_immune=False, subtract_id: str = None):
    exp_rows = database.query(
        """
        SELECT id, exp_rate, name
        FROM categories
        ORDER BY id
        """
    ).fetchall()

    for row in exp_rows:
        if row[2] == category_name:
            category_id = row[0]
            if amount in ('add', 'subtract'):
                amount = - row[1] if amount == 'subtract' else row[1]
            break

    total_multiplier = get_multipliers(user_id) if not multiplier_immune else 1

    database.update(
        """
        INSERT INTO levels (user_id, category_id, exp)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, category_id) DO
        UPDATE SET exp = levels.exp + EXCLUDED.exp
        """,
        (user_id, category_id, amount * total_multiplier)
    )

    # recalculate_exp_rate(exp_rows, category_id, subtract_id, False if amount >= 0 else True)

    # Level-up notifications:
    current_exp = (database.query(
        """
        SELECT exp
        FROM levels
        WHERE user_id = %s
        """,
        (user_id,)
    ).fetchone())[0]
    if calculate_level(current_exp - amount) < calculate_level(current_exp):
        if category_name.endswith('ing'):
            category = category_name[:-3].lower() + 'er'
        elif category_name.isupper():
            category = category_name + ' artist'
        elif category_name.endswith('ion'):
            category = category_name[:-3].lower() + 'or'
        user = client.get_user(user_id)
        if user is None:
            user = await client.fetch_user(user_id)
        if category:
            await lang.get("levels.level_up.1").send(user, level=str(calculate_level(current_exp)), category=category)
        else:
            await lang.get("levels.level_up.2").send(user, level=str(calculate_level(current_exp)),
                                                     category=category_name.lower() if not category_name.isupper() else category_name.upper())


added_exp = {}


# TODO: Fix the exp rate recalculation.
def recalculate_exp_rate(previous_rows, category_id, subtract_id=None, subtract=False):
    other_categories = len(previous_rows) - 1
    distance_from_center = [fabs(row[1] - 12) for row in previous_rows]
    previous_rows = list(previous_rows)

    if distance_from_center[category_id - 1] < 7:
        change_by = round(((distance_from_center[category_id - 1] * 11 + 7) / 142.857) / other_categories, 6)
    else:
        change_by = 0

    if subtract:
        change_by = - added_exp[subtract_id]
        added_exp.pop(subtract_id)
    else:
        added_exp[subtract_id] = change_by

    for i in range(len(previous_rows)):
        previous_rows[i] = list(previous_rows[i])[:-1]
        if previous_rows[i][0] != category_id:
            previous_rows[i][1] += change_by
        else:
            previous_rows[i][1] -= change_by * other_categories

        if not (5 <= previous_rows[i][1] <= 19):
            previous_rows[i][1] = 19 if previous_rows[i][1] > 19 else 5

    while True:
        try:
            database.cursor.executemany(
                """
                INSERT INTO categories (id, exp_rate)
                VALUES (%s,%s)
                ON CONFLICT (id) DO
                UPDATE SET exp_rate = EXCLUDED.exp_rate
                """,
                previous_rows
            )
            database.connection.commit()
            break
        except DatabaseError:
            database.connect()


def add_multiplier(user_id, multiplier, duration=None):
    database.update(
        """
        INSERT INTO multipliers (user_id, multiplier, end_time)
        VALUES (%s, %s, CURRENT_TIMESTAMP + %s)
        """,
        (user_id, multiplier, duration)
    )


def get_multipliers(user_id, raw=False):
    multipliers = database.query(
        """
        SELECT multiplier, end_time
        FROM multipliers
        WHERE user_id = %s
        ORDER BY end_time
        """,
        (user_id,)
    ).fetchall()
    total_multiplier = 1
    multipliers = list(multipliers)
    has_expired = False
    for i in range(len(multipliers) - 1, -1, -1):
        multiplier = multipliers[i]
        if multiplier[1] > datetime.now(timezone.utc):
            total_multiplier *= multiplier[0]
        else:
            has_expired = True
            multipliers.remove(multiplier)
    if has_expired:
        database.update(
            """
            DELETE FROM multipliers
            WHERE end_time <= CURRENT_TIMESTAMP
            """
        )

    if raw:
        return multipliers, total_multiplier
    return total_multiplier


def strfdelta(timedelta):
    hours, remainder = divmod(timedelta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds, microseconds = divmod(timedelta.microseconds, 1000)
    times = [
        f"{timedelta.days} day{'s' if timedelta.days != 1 else ''}",
        f"{hours} hour{'s' if hours != 1 else ''}",
        f"{minutes} minute{'s' if minutes != 1 else ''}",
        f"{seconds} second{'s' if seconds != 1 else ''}",
        f"{milliseconds} millisecond{'s' if milliseconds != 1 else ''}",
        f"{microseconds} microsecond{'s' if microseconds != 1 else ''}"
    ]
    time_string = times[0]
    for i in range(1, len(times)):
        if times[i][0] != '0':
            time_string += ', ' + times[i]
    return time_string


class Level(commands.Cog):
    """
    Average 11 exp.
    Exp rate: Float from 5 to 19.

    TODO: The notifications for levels and exp.
    """

    def __init__(self):
        with open("config.yml") as f:
            config = load(f, Loader=FullLoader)
            self.categories = config['categories']
            self.rda = config['servers']['rda']
        self.date_format = '%A, %B %d, %Y; %I:%M %p UTC'

    '''
    # For testing only:
    @commands.command()
    @conditions.manager_only()
    async def reset(self, ctx, *args):
        if any(arg.lower() in ('levels', 'all') for arg in args):
            database.update(
                """
                DELETE FROM levels
                """
            )
        if any(arg.lower() in ('categories', 'all') for arg in args):
            database.update(
                """
                UPDATE categories
                SET exp_rate = 11
                """
            )
        if any(arg.lower() in ('multipliers', 'all') for arg in args):
            database.update(
                """
                DELETE FROM multipliers
                """
            )

    @commands.command()
    @conditions.manager_only()
    async def exp(self, ctx, user_id, category, amount: int):
        category = category.capitalize() if category.lower() not in ('gfx', 'sfx') else category.upper()
        await add_exp(user_id, category, amount)
    '''

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji == lang.global_placeholders.get("emoji.solution") and reaction.message.author.id != user.id:
            category_name = None
            for category in self.categories:
                if reaction.message.channel.id in self.categories[category]:
                    category_name = category
                    break

            if category_name is None:
                return

            await add_exp(reaction.message.author.id, category_name, 'add',
                          subtract_id=f"{reaction.message.id}{user.id}")

        elif reaction.emoji == lang.global_placeholders.get("emoji.profile"):
            await reaction.remove(user)
            await self.profile(user, (reaction.message.author,))
        elif reaction.emoji in (
                lang.global_placeholders.get("emoji.next"), lang.global_placeholders.get("emoji.previous"),
                lang.global_placeholders.get("emoji.rewind"), lang.global_placeholders.get("emoji.fast_forward")) \
                and reaction.message.embeds and reaction.message.embeds[0].footer and f"{user}" in \
                reaction.message.embeds[0].footer.text:
            leaderboard = reaction.message.embeds[0]
            page = int(leaderboard.footer.text.split(' ')[1][:-1])
            if reaction.emoji == lang.global_placeholders.get("emoji.next"):
                page += 1
            elif reaction.emoji == lang.global_placeholders.get("emoji.previous"):
                if page > 1:
                    page -= 1
                else:
                    return
            elif reaction.emoji == lang.global_placeholders.get("emoji.rewind"):
                if page == 1:
                    return
                page = 1
            elif reaction.emoji == lang.global_placeholders.get("emoji.fast_forward"):
                page = -1

            shown_categories = [field.name for field in leaderboard.fields]
            has_ranks = False
            i = 0
            ranks_per_page = 5 if len(shown_categories) != 1 else 10
            for category in shown_categories:
                rank_strings = []
                if page == -1:
                    total_ranks = (database.query(
                        """
                        SELECT COUNT(user_id)
                        FROM levels JOIN categories
                        ON category_id = categories.id AND categories.name = %s
                        """,
                        (category,)
                    ).fetchone())[0]
                    if total_ranks <= 0:
                        leaderboard.set_field_at(i, name=category,
                                                 value="There are currently no rankings for this category.")
                        i += 1
                        continue
                    if int(leaderboard.footer.text.split(' ')[1][:-1]) == ceil(total_ranks / ranks_per_page):
                        return
                    page = ceil(total_ranks / ranks_per_page)

                rank_index = (page - 1) * ranks_per_page

                ranks = database.query(
                    """
                    SELECT user_id, exp
                    FROM levels JOIN categories
                    ON category_id = categories.id AND categories.name = %s
                    ORDER BY exp DESC
                    LIMIT %s OFFSET %s
                    """,
                    (category, ranks_per_page, rank_index)
                ).fetchall()

                if ranks:
                    has_ranks = True
                    for row in ranks:
                        rank_index += 1
                        mention = f"{'__' if row[0] == user.id else ''}<@{row[0]}>{'__' if row[0] == user.id else ''}"
                        exp = f"{lang.global_placeholders.get('s')}**Exp:** {row[1]}." if len(
                            shown_categories) == 1 else ''
                        rank_strings.append(f"**{rank_index})** {mention} Level {calculate_level(row[1])}.{exp}")
                        leaderboard.set_field_at(i, name=category,
                                                 value='\n\n'.join(rank_strings))
                else:
                    leaderboard.set_field_at(i, name=category,
                                             value="There are currently no rankings for this category.")
                i += 1
            if not has_ranks:
                return
            leaderboard.set_footer(text=f"Page: {page}.     " + leaderboard.footer.text.split(' ')[-1])
            await reaction.message.edit(embed=leaderboard)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if reaction.emoji == lang.global_placeholders.get("emoji.solution") and reaction.message.author.id != user.id:
            category_name = None
            for category in self.categories:
                if reaction.message.channel.id in self.categories[category]:
                    category_name = category
                    break

            if category_name is None:
                return

            await add_exp(reaction.message.author.id, category_name, 'subtract',
                          subtract_id=f"{reaction.message.id}{user.id}")

    @commands.command()
    async def profile(self, ctx, user: commands.Greedy[Member] = None):
        if ctx.guild and ctx.guild.id == self.rda:
            user = user[0] if user else ctx.author
        else:
            user = client.get_guild(self.rda).get_member(user[0].id if user else ctx.author.id)

        ranks = database.query(
            """
            SELECT categories.name, levels.exp,
            RANK () OVER (
                PARTITION BY levels.category_id
                ORDER BY levels.exp
            ) rank
            FROM levels JOIN categories
            ON levels.category_id = categories.id AND levels.user_id = %s
            """,
            (user.id,)
        ).fetchall()

        multipliers, total_multiplier = get_multipliers(user.id, raw=True)

        rank_strings = [
            f"`{rank[0]}` Rank: {rank[2]}.\n**Level:** {calculate_level(rank[1])}.{lang.global_placeholders.get('s')}**Total Exp:** {rank[1]}.\nExp Left Until Next Level: {calculate_level(rank[1], True)[2] - calculate_level(rank[1], True)[1]}."
            for rank in ranks]
        multiplier_strings = "None." if not multipliers else [
            f"**Multiplier: {multiplier[0]}x**\nExpiration Date: {multiplier[1].strftime(self.date_format) + '.' if multiplier[1] else 'Never.'}"
            for multiplier in multipliers]

        await lang.get("profile").send(ctx, user_name=str(user), user_id=str(user.id), avatar_url=str(user.avatar_url),
                                       nickname='' if user.name == user.display_name else f"**Nickname:** {user.display_name}",
                                       levels='\n'.join(
                                           rank_strings) if rank_strings else "There are currently no levels to display.",
                                       multipliers=multiplier_strings if not multipliers else f"__Total Multiplier: {round(total_multiplier, 4)}x__\n\n" + '\n'.join(
                                           multiplier_strings),
                                       join_server=user.joined_at.strftime(self.date_format),
                                       join_discord=user.created_at.strftime(self.date_format),
                                       server_duration=strfdelta(datetime.utcnow() - user.joined_at),
                                       discord_duration=strfdelta(datetime.utcnow() - user.created_at))

    @commands.command(aliases=("lb", "ranks", "ranking", "rankings", "levels", "leaderboards"))
    async def leaderboard(self, ctx, category=None):
        prefix = get_prefix(ctx.guild.id)

        shown_categories = []
        if category:
            category = category.upper() if category.upper() in ("GFX", "SFX") else category.capitalize()
            if category not in self.categories:
                await lang.get("error.invalid_category").send(ctx, category=category, prefix=prefix)
                return
            shown_categories.append(category)
        else:
            shown_categories = [category_name for category_name in self.categories]

        rank_strings = {}
        lb_node = deepcopy(lang.get("levels.leaderboard").replace(prefix=prefix, page="1", user=f"{ctx.author}"))

        for category in shown_categories:
            ranks = database.query(
                """
                SELECT user_id, exp
                FROM levels JOIN categories
                ON category_id = categories.id AND categories.name = %s
                ORDER BY exp DESC
                LIMIT %s
                """,
                (category, 5 if len(shown_categories) != 1 else 10)
            ).fetchall()

            rank_strings[category] = []
            i = 0
            for row in ranks:
                i += 1
                mention = f"{'__' if row[0] == ctx.author.id else ''}<@{row[0]}>{'__' if row[0] == ctx.author.id else ''}"
                exp = f"{lang.global_placeholders.get('s')}**Exp:** {row[1]}." if len(shown_categories) == 1 else ''
                rank_strings[category].append(f"**{i})** {mention} Level {calculate_level(row[1])}.{exp}")

            lb_node.nodes[0].args['embed'].add_field(name=category,
                                                     value='\n\n'.join(rank_strings[category]) if rank_strings[
                                                         category] else "There are currently no rankings for this category.")
        await lb_node.send(ctx)

    @commands.command()
    async def categories(self, ctx):
        rows = database.query(
            """
            SELECT name, exp_rate
            FROM categories
            ORDER BY id
            """
        ).fetchall()
        categories_node = deepcopy(lang.get("levels.categories"))
        for row in rows:
            categories_node.nodes[0].args['embed'].add_field(name=row[0],
                                                             value=f"Channels:\n<#{'> <#'.join(str(channel) for channel in self.categories[row[0]])}>\nExp Rate: {row[1]}")
        await categories_node.send(ctx)

    @commands.command()
    @conditions.manager_only()
    async def multiplier(self, ctx, user: commands.Greedy[User] = None, multiplier: float = None, duration=None):
        if duration:
            try:
                duration = parse_interval(duration, maximum=datetime.max - datetime.now())
            except OverflowError:
                await lang.get("error.multiplier.duration").send(ctx, duration=strfdelta(datetime.max - datetime.now()), date=datetime.max.strftime(self.date_format))
                return
            if duration is None:
                await lang.get("error.interval.parse").send(ctx)
                return
        if (user and multiplier is None) or ((multiplier is not None) and not (1 < multiplier <= 14641)):
            if multiplier is None:
                await lang.get("multiplier.usage").send(ctx, prefix=get_prefix(ctx.guild.id))
            else:
                await lang.get("error.multiplier.invalid").send(ctx, multiplier=str(multiplier))
            return
        if user:
            add_multiplier(user[0].id, multiplier, duration)
            await lang.get("multiplier.success").send(ctx, multiplier=str(multiplier), user=user[0].mention,
                                                      expire=(datetime.utcnow() + duration).strftime(
                                                          self.date_format) if duration else "Never.",
                                                      duration=strfdelta(duration) if duration else "Forever.")
        else:
            await lang.get("multiplier.usage").send(ctx, prefix=get_prefix(ctx.guild.id))
