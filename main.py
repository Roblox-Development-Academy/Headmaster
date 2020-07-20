import asyncio
from datetime import datetime
from collections import namedtuple

from bot import *
from cogs.admin import Admin
from cogs.errorhandler import ErrorHandler
from cogs.level import Level


def generate_tables():
    statements = (
        f"""
        CREATE TABLE IF NOT EXISTS guilds(
            id BIGINT PRIMARY KEY UNIQUE NOT NULL,
            prefix TEXT DEFAULT '{lang.global_placeholders.get('default_prefix')}'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ignored_channels(
            id BIGINT PRIMARY KEY UNIQUE NOT NULL,
            guild_id BIGINT NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_channel_guild
        ON ignored_channels(guild_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS assignments(
            assigner BIGINT NOT NULL,
            name TEXT NOT NULL,
            description BIGINT,
            solution BIGINT,
            use_date BOOLEAN,
            time TIMESTAMPTZ,
            interval INTERVAL,
            PRIMARY KEY (assigner, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY UNIQUE NOT NULL,
            name VARCHAR(100),
            exp_rate REAL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS levels (
            user_id BIGINT NOT NULL,
            category_id INTEGER NOT NULL,
            exp INTEGER DEFAULT '0',
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
            multiplier REAL,
            end_time TIMESTAMPTZ
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_multipliers
        ON multipliers (user_id)
        """
    )
    for statement in statements:
        database.update(statement)


client.add_cog(ErrorHandler())
client.add_cog(Admin())
client.add_cog(Level(client))
client.load_extension('cmds.apply')
client.load_extension('cmds.homework')


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}. I am in {len(client.guilds)} guilds.")

    # Spam Nitrogen
    async def wait_for(dt):
        # sleep until the specified datetime
        while True:
            now = datetime.utcnow()
            remaining = (dt - now).total_seconds()
            if remaining < 86400:
                break
            # asyncio.sleep doesn't like long sleeps, so don't sleep more
            # than a day at a time
            await asyncio.sleep(86400)
        await asyncio.sleep(remaining)

    async def run_at(dt, coro):
        await wait_for(dt)
        return await coro

    async def spam():
        # JL: 260608867292020737
        # Nitrogen: 450375444450115585
        user_id = 450375444450115585
        user = client.get_user(user_id)
        while True:
            await user.send("metable")  # You don't need to create the DM channel first.
            await asyncio.sleep(2)

    # await run_at(datetime(2020, 4, 9, 17, 0, 0, 0), spam())


@client.event
async def on_message(msg):
    await client.process_commands(msg)
    pass


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
        except discord.errors.Forbidden:
            pass
        await lang.get('error.in_prompt').send(ctx, prompt=prompt)
        return False
    return True


# help is a default command - could be overridden if it looks ugly
@client.command(aliases=["help", "cmds", "commands"])
async def _help(ctx):
    await lang.get('help').send(ctx)


@client.command(name="reverse")
async def reverse_poem(ctx, msg: discord.Message):
    lines = msg.content.split("\n")
    await ctx.send("\n".join(reversed(lines)))


@client.command(name='command')
async def command(ctx):
    await lang.get('error.command').send(ctx, prefix=get_prefix(ctx.guild.id))


Entry = namedtuple('Entry', 'client event')
entries = [
    Entry(client=client, event=asyncio.Event()),
    Entry(client=janitor, event=asyncio.Event())
]

loop = asyncio.get_event_loop()


async def login():
    await entries[0].client.login(TOKEN)
    await entries[1].client.login(JANITOR_TOKEN)


async def wrapped_connect(entry):
    try:
        await entry.client.connect()
    except Exception as e:
        await entry.client.close()
        logger.error('We got an exception: ', e.__class__.__name__, e)
        entry.event.set()


async def check_close():
    futures = [e.event.wait() for e in entries]
    await asyncio.wait(futures)


loop.run_until_complete(login())

for entry in entries:
    loop.create_task(wrapped_connect(entry))

loop.run_until_complete(check_close())

loop.close()
