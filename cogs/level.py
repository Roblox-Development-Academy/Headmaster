from discord import User
from datetime import datetime, timezone
from math import floor, ceil, fabs
from copy import deepcopy
from psycopg2 import DatabaseError
from random import seed, uniform
from typing import Optional

from bot import *
from utils.common import parse_interval, td_format
import conditions
from utils.language import LangManager

profession_names = {
    "Scripting": "scripter",
    "Animation:": "animator",
    "Modeling:": "modeler",
    "Building": "builder",
    "GFX": "GFX artist",
    "Audio Engineering": "Audio Engineer"
}


def get_profession_name(category_name: str) -> Optional[str]:
    profession = profession_names.get(category_name)
    if profession:
        return profession
    if category_name.endswith("ering"):
        return category_name[:-3].lower()
    elif category_name.endswith('ing'):
        return category_name[:-3].lower() + 'er'
    elif category_name.isupper():
        return category_name + ' artist'
    elif category_name.endswith('ion'):
        return category_name[:-3].lower() + 'or'
    return None


def get_exp_bar(level_exp, total_level_exp, num_squares: int = 8) -> str:
    num_progress = floor((level_exp / total_level_exp) * num_squares)
    exp_bar = "💠" * num_progress + \
              "🔶" * (num_squares - num_progress)
    return exp_bar


def calculate_level(exp, is_profile=False):
    level_exp = 11
    exp_left = exp
    remainder = exp_left
    level = -1
    while exp_left >= 0:
        level += 1
        level_exp = 22 + 11 * floor(level / 3)

        remainder = exp_left
        exp_left = exp_left - level_exp
    if is_profile:
        return level, remainder, level_exp
    return level


category_rows: list


def get_exp_rows():
    global category_rows

    category_rows = database.query(
        """
        SELECT id, exp_rate, name
        FROM categories
        ORDER BY id
        """
    ).fetchall()
    total_exp = database.query(
        """
        SELECT category_id, SUM(exp)
        FROM levels
        GROUP BY category_id
        ORDER BY category_id
        """
    ).fetchall()
    for i in range(len(category_rows)):
        category_rows[i] = list(category_rows[i])
        for index in range(0, len(total_exp) if len(total_exp) <= i + 1 else i + 1):
            if total_exp[index][0] == i + 1:
                category_rows[i].append(int(total_exp[index][1]))
                break
        if len(category_rows[i]) < 4:
            category_rows[i].append(0)

    print(category_rows)
    print(total_exp)


get_exp_rows()


async def add_exp(user_id, category_name, amount, seed_id=None, multiplier_immune=False, giver: discord.User = None):
    category_id = None
    category_name = category_name.capitalize() if category_name.upper() not in ('GFX', 'SFX') else category_name.upper()

    for row in category_rows:
        if row[2] == category_name:
            category_id = row[0]
            if amount in ('add', 'subtract'):
                amount = - row[1] if amount == 'subtract' else row[1]
            break

    multipliers, total_multiplier = get_multipliers(user_id, True) if not multiplier_immune else ([], 1)

    database.update(
        """
        INSERT INTO levels (user_id, category_id, exp)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, category_id) DO
        UPDATE SET exp = levels.exp + EXCLUDED.exp
        """,
        (user_id, category_id, amount * total_multiplier)
    )
    category_rows[category_id - 1][3] += amount * total_multiplier

    if not any(category[3] < 22 for category in category_rows):
        recalculate_exp_rate(seed_id)
    if amount < 0:
        return

    # Level-up notifications:
    member: discord.Member = rda.get_member(user_id)
    current_exp = (database.query(
        """
        SELECT exp
        FROM levels
        WHERE user_id = %s AND category_id = %s
        """,
        (user_id, category_id)
    ).fetchone())[0]
    profession = get_profession_name(category_name)
    level, level_exp, total_level_exp = calculate_level(current_exp, True)
    user = member or client.get_user(user_id)
    if user is None:
        user = await client.fetch_user(user_id)
    if calculate_level(current_exp - amount) < level:  # Leveled up
        if member and roles['level_noalert'] in member.roles:
            return
        title = f"LEVELED UP TO LEVEL {level}"
    else:
        if member and roles['experience_noalert'] in member.roles:
            return
        if total_multiplier == 1:
            title = f"+ {amount} {category_name} EXP"
        else:
            title = f"+ {amount} * {total_multiplier} {category_name} EXP"
    exp_bar = get_exp_bar(level_exp, total_level_exp)
    str_multipliers = "\n".join([f"%bullet% x {multiplier}: {td_format(end_time - datetime.now(timezone.utc))}"
                                 for multiplier, end_time in multipliers]) or "*No active multipliers*"
    str_multipliers = LangManager.replace(str_multipliers)
    await lang.get('levels.experience_up').send(user, title=title, level=level, experience=amount * total_multiplier,
                                                exp_bar=exp_bar, current_exp=level_exp, total_level_exp=total_level_exp,
                                                multipliers=str_multipliers, profession=profession,
                                                giver=giver.mention if giver else "null")


def recalculate_exp_rate(seed_id: int = None):
    seed(seed_id)
    total_exp = sum([row[3] for row in category_rows])
    for i in range(len(category_rows)):
        amount = (11 * len(category_rows) - (11 * len(category_rows) * category_rows[i][3])
                  / total_exp) / (len(category_rows) - 1)
        amount = amount + uniform(-0.51, 0.51)
        if not 5 <= amount <= 19:
            amount = 5 if category_rows[i][1] < 5 else 19
        category_rows[i][1] = amount

    while True:
        try:
            database.cursor.executemany(
                """
                INSERT INTO categories (id, exp_rate)
                VALUES (%s,%s)
                ON CONFLICT (id) DO
                UPDATE SET exp_rate = EXCLUDED.exp_rate
                """,
                [(row[0], row[1]) for row in category_rows]
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
        if multiplier[1] is None or multiplier[1] > datetime.now(timezone.utc):
            total_multiplier *= multiplier[0]
        else:
            has_expired = True
            multipliers.pop(i)
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


class Level(commands.Cog):
    """
    Average 11 exp.
    Exp rate: Float from 5 to 19.
    """

    def __init__(self):
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
        if any(arg.lower().startswith("test_levels") for arg in args):
            database.update(
                """
                DELETE FROM levels
                WHERE user_id = 697655651127525498
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
        await ctx.send(embed=Embed(title="Reset Successful",
                                   description='.\n'.join([arg.capitalize() for arg in args]) + '.',
                                   colour=int(lang.global_placeholders.get("color.success"), 16)))
    '''

    @commands.command()
    @conditions.manager_only()
    async def exp_add(self, ctx, users: commands.Greedy[User] = None, category=None, amount=None):
        if category:
            category = category.capitalize() if category.upper() not in ('GFX', 'SFX') else category.upper()
        try:
            amount = float(amount)
        except ValueError:
            amount = None

        if (not users) or (category not in level_categories) or (amount is None):
            await lang.get("exp.help").send(ctx, prefix=get_prefix(rda.id))
            return

        for user in users:
            await add_exp(user.id, category, amount, giver=ctx.author)
        users_string = users[0].mention
        if len(users) > 1:
            users_string = ', '.join(user.mention for user in users[:-1]) + (',' if len(users) != 2 else '') \
                           + " and " + users[-1].mention
        await lang.get("exp.success").send(ctx, category=category, amount=str(round(fabs(amount))),
                                           action='given to' if amount >= 0 else 'taken away from', users=users_string)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji == lang.global_placeholders.get("emoji.solution")\
                and reaction.message.author.id != user.id and reaction.message.author.bot is False:
            category_name = None
            for category in level_categories:
                if reaction.message.channel.id in level_categories[category]:
                    category_name = category
                    break

            if category_name is None:
                return

            await add_exp(reaction.message.author.id, category_name, 'add', seed_id=reaction.message.id - user.id,
                          giver=user)

        elif reaction.emoji == lang.global_placeholders.get("emoji.profile"):
            await reaction.remove(user)
            await self.profile(user, member=reaction.message.author)
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

                ranks = database.query(
                    """
                    SELECT user_id, exp, rank
                    FROM (
                        SELECT levels.user_id, exp,
                            RANK () OVER (
                            ORDER BY exp DESC
                            ) rank
                        FROM levels JOIN categories
                        ON category_id = categories.id AND categories.name = %s
                    ) leaderboard
                    LIMIT %s OFFSET %s
                    """,
                    (category, ranks_per_page, (page - 1) * ranks_per_page)
                ).fetchall()

                if ranks:
                    has_ranks = True
                    for row in ranks:
                        mention = f"{'__' if row[0] == user.id else ''}<@{row[0]}>{'__' if row[0] == user.id else ''}"
                        exp = f"{lang.global_placeholders.get('s')}**Exp:** {row[1]}." if len(
                            shown_categories) == 1 else ''
                        rank_strings.append(f"**{row[2]})** {mention} Level {calculate_level(row[1])}.{exp}")
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
        if reaction.emoji == lang.global_placeholders.get("emoji.solution")\
                and reaction.message.author.id != user.id and reaction.message.author.bot is False:
            category_name = None
            for category in level_categories:
                if reaction.message.channel.id in level_categories[category]:
                    category_name = category
                    break

            if category_name is None:
                return

            await add_exp(reaction.message.author.id, category_name, 'subtract', seed_id=reaction.message.id - user.id,
                          giver=user)

    @commands.command()
    async def profile(self, ctx, *, member: Optional[discord.Member] = None):
        if member is None:
            member = rda.get_member(ctx.author.id)

        ranks = database.query(
            """
            SELECT category, exp, rank
            FROM (
                SELECT levels.user_id, categories.name AS category, exp,
                    RANK () OVER (
                    PARTITION BY levels.category_id
                    ORDER BY levels.exp DESC
                    ) rank
                FROM levels JOIN categories
                ON levels.category_id = categories.id
            ) leaderboard
            WHERE user_id = %s
            """,
            (member.id,)
        ).fetchall()

        multipliers, total_multiplier = get_multipliers(member.id, raw=True)

        rank_strings = [
            f"`{category}` Rank: {rank}.\n**Level:** {level}." +
            f"{lang.global_placeholders.get('s')}**Total Exp:** {exp}.\n{get_exp_bar(level_exp, total_level_exp)} " +
            f"{level_exp}/{total_level_exp}"
            for category, exp, rank, level, level_exp, total_level_exp
            in map(lambda info: (*info, *calculate_level(info[1], True)), ranks)]
        multiplier_strings = "None." if not multipliers else [
            f"**Multiplier: {multiplier[0]}x**\n" +
            f"{td_format(multiplier[1] - datetime.now(timezone.utc)) if multiplier[1] else 'Permanent.'} "
            for multiplier in multipliers]

        await lang.get("profile").send(ctx, user_name=str(member), user_id=str(member.id),
                                       avatar_url=str(member.avatar_url),
                                       nickname='' if member.name == member.display_name
                                       else f"**Nickname:** {member.display_name}",
                                       levels='\n'.join(rank_strings) if rank_strings
                                       else "There are currently no levels to display.",
                                       multipliers=multiplier_strings if not multipliers
                                       else f"__Total Multiplier: {round(total_multiplier, 4)}x__\n\n" + '\n'.join(
                                           multiplier_strings),
                                       join_server=member.joined_at.strftime(self.date_format),
                                       join_discord=member.created_at.strftime(self.date_format),
                                       server_duration=td_format(datetime.utcnow() - member.joined_at),
                                       discord_duration=td_format(datetime.utcnow() - member.created_at))

    @commands.command(aliases=("lb", "rank", "ranks", "ranking", "rankings", "levels", "leaderboards", "exp", "xp"))
    async def leaderboard(self, ctx, category=None):
        prefix = get_prefix(rda.id)

        shown_categories = []
        if category:
            category = category.upper() if category.upper() in ("GFX", "SFX") else category.capitalize()
            if category not in level_categories:
                await lang.get("error.invalid_category").send(ctx, category=category, prefix=prefix)
                return
            shown_categories.append(category)
        else:
            shown_categories = [category_name for category_name in level_categories]

        rank_strings = {}
        lb_node = deepcopy(lang.get("levels.leaderboard").replace(prefix=prefix, page="1", user=f"{ctx.author}"))

        for category in shown_categories:
            ranks = database.query(
                """
                SELECT user_id, exp,
                    RANK () OVER (
                    ORDER BY levels.exp DESC
                    ) rank
                FROM levels JOIN categories
                ON category_id = categories.id AND categories.name = %s
                ORDER BY exp DESC
                LIMIT %s
                """,
                (category, 5 if len(shown_categories) != 1 else 10)
            ).fetchall()

            rank_strings[category] = []
            for row in ranks:
                mention = f"{'__' if row[0] == ctx.author.id else ''}<@{row[0]}>" \
                          f"{'__' if row[0] == ctx.author.id else ''}"
                exp = f"{lang.global_placeholders.get('s')}**Exp:** {row[1]}." if len(shown_categories) == 1 else ''
                rank_strings[category].append(f"**{row[2]})** {mention} Level {calculate_level(row[1])}.{exp}")

            lb_node.nodes[0].args['embed'].add_field(name=category,
                                                     value='\n\n'.join(rank_strings[category]) if rank_strings[category]
                                                     else "There are currently no rankings for this category.")
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
            channel_info = f"Channels:\n<#{'> <#'.join(str(channel) for channel in level_categories[row[0]])}>" \
                           f"\nExp Rate: " \
                           f"{(str(row[1] - 0.51) + ' - ' + str(row[1] + 0.51)) if not any(category[3] < 22 for category in category_rows) else row[1]}"
            categories_node.nodes[0].args['embed'].add_field(name=row[0], value=channel_info)
        await categories_node.send(ctx)

    @commands.command()
    @conditions.manager_only()
    async def multiplier(self, ctx, user: commands.Greedy[User] = None, multiplier: float = None, duration=None):
        if duration:
            try:
                duration = parse_interval(duration, maximum=datetime.max - datetime.now())
            except OverflowError:
                await lang.get("error.multiplier.duration").send(ctx, duration=td_format(datetime.max - datetime.now()),
                                                                 date=datetime.max.strftime(self.date_format))
                return
            if duration is None:
                await lang.get("error.interval.parse").send(ctx)
                return
        if (user and multiplier is None) or ((multiplier is not None) and not (0 <= multiplier <= 14641)):
            if multiplier is None:
                if ctx.guild:
                    await lang.get("multiplier.usage").send(ctx, prefix=get_prefix(ctx.guild.id))
                else:
                    await lang.get("multiplier.usage").send(ctx, prefix=lang.global_placeholders.get('default_prefix'))
            else:
                await lang.get("error.multiplier.invalid").send(ctx, multiplier=str(multiplier))
            return
        if user:
            add_multiplier(user[0].id, multiplier, duration)
            await lang.get("multiplier.success").send(ctx, multiplier=str(multiplier), user=user[0].mention,
                                                      expire=(datetime.utcnow() + duration).strftime(
                                                          self.date_format) if duration else "Never",
                                                      duration=td_format(duration) if duration else "Forever")
        else:
            if ctx.guild:
                await lang.get("multiplier.usage").send(ctx, prefix=get_prefix(ctx.guild.id))
            else:
                await lang.get("multiplier.usage").send(ctx, prefix=lang.global_placeholders.get('default_prefix'))
