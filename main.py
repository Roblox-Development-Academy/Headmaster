import asyncio
import re

import uvicorn

from bot import *
from bot import in_prompt
from cogs.admin import Admin
from cogs.errorhandler import ErrorHandler
import conditions
from web.app import app


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
        CREATE INDEX IF NOT EXISTS idx_channel_guild ON ignored_channels(guild_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS assignments(
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
        CREATE TABLE IF NOT EXISTS submissions(
            submitter BIGINT NOT NULL,
            assigner BIGINT NOT NULL,
            name TEXT NOT NULL,
            submitted_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (submitter, assigner, name),
            CONSTRAINT fk_assignment FOREIGN KEY(assigner, name) REFERENCES assignments(assigner, name)
            ON DELETE CASCADE
        )
        """
    )
    for statement in statements:
        database.update(statement)


generate_tables()


client.add_cog(ErrorHandler())
client.add_cog(Admin())
client.load_extension('cmds.apply')
client.load_extension('cmds.homework')


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}. I am in {len(client.guilds)} guilds.")


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


@client.command(aliases=('exec',))
@conditions.manager_only()
async def execute(ctx: commands.Context):
    content = ctx.message.content
    matcher = re.compile(r'```\w+$(.+)```', re.MULTILINE | re.DOTALL)
    code = matcher.search(content)
    if code:
        try:
            exec(code.group(1), globals(), locals())
        except Exception as e:
            await ctx.send(str(e))
        await ctx.message.add_reaction(lang.global_placeholders['emoji.gotcha'])
    else:
        await ctx.message.add_reaction(lang.global_placeholders['emoji.error'])


loop = asyncio.get_event_loop()
loop.create_task(client.start(TOKEN))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
