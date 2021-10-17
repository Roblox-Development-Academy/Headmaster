import asyncio
import re
import traceback

import uvicorn

import bot
from bot import *
from web.app import app


async def run():
    await client.wait_until_ready()
    await asyncio.sleep(1)
    from cogs.admin import Admin
    from cogs.errorhandler import ErrorHandler
    from cogs.level import Level
    from cogs.report import Report
    from cogs.reaction_roles import ReactionRoles
    from cogs import errorhandler
    import conditions

    def generate_tables():
        statements = (
            f"""
            CREATE TABLE IF NOT EXISTS guilds (
                id BIGINT PRIMARY KEY UNIQUE NOT NULL,
                prefix TEXT DEFAULT '{lang.global_placeholders.get('default_prefix')}'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ignored_channels (
                id BIGINT PRIMARY KEY UNIQUE NOT NULL,
                guild_id BIGINT NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_channel_guild
            ON ignored_channels(guild_id)
            """,
            """
            CREATE TABLE IF NOT EXISTS assignments (
                assigner BIGINT NOT NULL,
                name TEXT NOT NULL,
                description BIGINT,
                solution BIGINT,
                delete_after_date BOOLEAN,
                date TIMESTAMPTZ,
                interval INTERVAL,
                PRIMARY KEY (assigner, name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS submissions (
                submitter BIGINT NOT NULL,
                assigner BIGINT NOT NULL,
                name TEXT NOT NULL,
                submitted_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (submitter, assigner, name),
                CONSTRAINT fk_assignment FOREIGN KEY(assigner, name) REFERENCES assignments(assigner, name)
                ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS classes (
                teacher BIGINT NOT NULL,
                name TEXT NOT NULL,
                message BIGINT,
                guild BIGINT,
                channel BOOLEAN,
                voice_channel BOOLEAN,
                starting_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (teacher, name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY UNIQUE NOT NULL,
                name VARCHAR(100) UNIQUE,
                exp_rate REAL DEFAULT 11
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS levels (
                user_id BIGINT NOT NULL,
                category_id INTEGER NOT NULL,
                exp REAL DEFAULT '0',
                PRIMARY KEY (user_id, category_id),
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_leaderboard
            ON levels (category_id, exp DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS multipliers (
                user_id BIGINT,
                multiplier REAL NOT NULL,
                end_time TIMESTAMPTZ
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_multipliers
            ON multipliers (user_id)
            """
        )
        upsert_statements = (
            """
            INSERT INTO categories (name)
            VALUES
                ('Scripting'),
                ('Animation'),
                ('Modeling'),
                ('Building'),
                ('GFX'),
                ('Audio Engineering')
            ON CONFLICT (name) DO NOTHING
            """,
        )
        for statement in statements:
            database.update(statement)
        for statement in upsert_statements:
            database.update(statement)

    generate_tables()

    client.add_cog(ErrorHandler())
    client.add_cog(Admin())
    client.add_cog(Level())
    client.add_cog(Report())
    client.add_cog(ReactionRoles())
    client.load_extension('cmds.apply')
    client.load_extension('cmds.homework')
    client.load_extension('cmds.class')

    @client.check
    async def globally_ignore_channels(ctx):
        if database.query(
            """
            SELECT id
            FROM ignored_channels
            WHERE id = %s
            """,
            (ctx.channel.id,)
        ).fetchone() is None:
            return True
        else:
            await ctx.message.delete()
            await lang.get('error.ignored_channel').send(ctx)
            return False

    @client.check
    async def globally_ignore_banned(ctx):
        # TODO
        return True

    @client.check
    async def ignore_in_prompt(ctx):
        prompt = in_prompt.get(ctx.message.author.id)
        if prompt:
            try:
                await ctx.message.delete()
            except nextcord.errors.Forbidden:
                pass
            await lang.get('error.in_prompt').send(ctx, prompt=prompt)
            return False
        return True

    # help is a default command - could be overridden if it looks ugly
    @client.command(aliases=["help", "cmds", "commands"])
    async def _help(ctx):
        await lang.get('help').send(ctx)

    @client.command(name="reverse")
    async def reverse_poem(ctx, msg: nextcord.Message):
        lines = msg.content.split("\n")
        await ctx.send("\n".join(reversed(lines)))

    @client.command(name='command')
    async def command(ctx):
        await lang.get('error.command').send(ctx, prefix=get_prefix(ctx.guild.id))

    @client.command(aliases=('reminder',))
    @commands.cooldown(1, 60*5, type=commands.BucketType.user)
    async def remind(ctx):
        try:
            await ctx.message.delete()
        except nextcord.Forbidden:
            pass
        await lang.get('remind').send(ctx)

    @remind.error
    async def remind_error(ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            try:
                await ctx.message.delete()
            except nextcord.Forbidden:
                pass
            await lang.get('error.cooldown').send(ctx.author,
                                                  seconds_left=round(remind.get_cooldown_retry_after(ctx), 2))
        else:
            await errorhandler.process(ctx, error)

    @client.command(aliases=('exec',))
    @conditions.manager_only()
    async def execute(ctx: commands.Context):
        content = ctx.message.content
        matcher = re.compile(r'(-s)?\s*```\w+$(.+)```', re.MULTILINE | re.DOTALL)
        code = matcher.search(content)
        if code:
            try:
                exec(f"async def __ex(ctx):\n  " + '\n  '.join(code.group(2).split('\n')),
                     {**globals(), **locals()}, locals())
                result = await locals()['__ex'](ctx)
                await ctx.message.add_reaction(lang.global_placeholders['emoji.gotcha'])
            except Exception as e:
                await ctx.send(f"```{traceback.format_exc()}```" if code.group(1) else str(e))
                await ctx.message.add_reaction(lang.global_placeholders['emoji.error'])
        else:
            await ctx.message.add_reaction(lang.global_placeholders['emoji.no'])

    @client.command()
    @conditions.manager_only()
    async def setup(ctx: commands.Context, info_channel: nextcord.TextChannel):
        messages = [(await node.send(info_channel, classes_channel=bot.channels['class'].mention,
                                     commands_channel=bot.channels['bot'].mention, mutate=True))
                    for node in lang.get('info_channel').nodes[:-1]]
        links = {"link" + str(i): messages[msg_i].jump_url for i, msg_i in zip(range(7), (1, 2, 4, 6, 8, 10, 12))}
        await lang.get('info_channel').nodes[-1].send(info_channel, **links)
        await ReactionRoles.add_msg('profession', messages[11])
        for i in range(13, 17):
            await ReactionRoles.add_msg('settings', messages[i], i - 13)
        await ctx.message.add_reaction(lang.global_placeholders['emoji.gotcha'])

loop = asyncio.get_event_loop()
loop.create_task(run())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
