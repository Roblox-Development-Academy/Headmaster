from dotenv import load_dotenv
load_dotenv()
import asyncio
import datetime
from collections import namedtuple

import pytz

from bot import *
from cogs.admin import Admin
from cogs.errorhandler import ErrorHandler


def generate_tables():
    statements = (
        f"""
        CREATE TABLE IF NOT EXISTS guilds(
            id BIGINT PRIMARY KEY UNIQUE NOT NULL,
            prefix TEXT DEFAULT '{DEFAULT_PREFIX}'
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_guild_id ON guilds(id)
        """,
        """
        CREATE TABLE IF NOT EXISTS ignored_channels(
            id BIGINT PRIMARY KEY UNIQUE NOT NULL,
            guild_id BIGINT NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_channel_id ON ignored_channels(id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_channel_guild ON ignored_channels(guild_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS assignments(
            assigner BIGINT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            description BIGINT,
            solution BIGINT,
            use_time BOOLEAN,
            time TIMESTAMPTZ (0),
            interval INTERVAL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_hw_assigner ON assignments(assigner)
        """
    )
    for statement in statements:
        database.update(statement)


client.add_cog(ErrorHandler(client))
client.add_cog(Admin())


@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}. I am in {len(client.guilds)} guilds.")

    # Spam Nitrogen
    async def wait_for(dt):
        # sleep until the specified datetime
        while True:
            now = datetime.datetime.now(pytz.utc)
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
        await user.create_dm()
        dm = user.dm_channel
        while True:
            await dm.send("metable")
            await asyncio.sleep(2)

    # await run_at(datetime.datetime(2020, 4, 9, 17, 0, 0, 0, pytz.UTC), spam())

tracked_channels = []


@client.event
async def on_message(msg):
    await client.process_commands(msg)
    if msg.channel in tracked_channels:
        await msg.add_reaction('\U0001f983')
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
        embed = discord.Embed(title=f"{EMOJIS['error']} You cannot use commands in this channel", colour=EMBED_COLORS['error'],
                              description="This channel is ignored by the bot. Please use another channel to execute "
                                          "commands.")
        warning = await ctx.send(embed=embed)
        await warning.delete(delay=3)
        return False


@client.check
async def globally_ignore_banned(ctx):
    # TODO
    return True


# help is a default command - could be overridden if it looks ugly
@client.command(aliases=["help", "botcommands"])
async def _help(ctx):
    embed = discord.Embed(title="Headmaster - Commands", colour=EMBED_COLORS["info"],
                          description="*Custom bot of [**Roblox Development Academy**]("
                                      "https://discord.gg/NxuhkqH)*\n*Dedicated to providing a perfect environment "
                                      "for teaching and learning.*")

    embed.set_footer(text="Made by JL for Roblox Development Academy",
                     icon_url="https://cdn.discordapp.com/avatars/260608867292020737/6e171a1f5883419ac89a52695c659ba5"
                              ".png?size=2048")

    general_commands = "**help** - Shows this message\n" \
                       "**profile** - View someone's profile\n" \
                       "**report** - Report a message with inappropriate contents\n" \
                       "**bookmark** - Bookmark a message for later reference"

    teacher_commands = "**apply** - Apply for teacher role\n" \
                       "**class** - Create a new class"

    homework_commands = "*Give students assignments to complete and a solution to check afterwards.*\n\n" \
                        "**hw** - View your own or others' created assignments\n" \
                        "**hw submit** - For students; submit an assignment\n" \
                        "**hw assign** - For teachers and tutors; create an assignment and a solution"

    admin_commands = "**getprefix** - Show the server command prefix\n" \
                     "**setprefix** - Set the server command prefix\n" \
                     "**ignore** - Choose channels for the bot to ignore"

    reaction_commands = "*React to a message with one of these emojis*\n\n" \
                        "**profile** - View the message author's profile\n" \
                        "**report** - Report a message with inappropriate contents\n" \
                        "**bookmark** - Bookmark a message for later reference\n" \
                        "**submit_hw** - Submit an assignment to the message author"

    embed.add_field(name="General Commands", value=general_commands)
    embed.add_field(name="Teacher Commands", value=teacher_commands, inline=False)
    embed.add_field(name="Homework Commands", value=homework_commands, inline=False)
    embed.add_field(name='Administrator Commands', value=admin_commands, inline=False)
    embed.add_field(name='Reaction Commands', value=reaction_commands, inline=False)

    await ctx.send(embed=embed)


@client.command(name='command')
async def command(ctx):
    embed = discord.Embed(title=f"{EMOJIS['error']} Unrecognized Command", colour=EMBED_COLORS["error"],
                          description=f"That's not an actual command, silly! It was an example. For a list of real "
                                      f"commands, use `{ctx.prefix}commands`")

    await ctx.send(embed=embed)


Entry = namedtuple('Entry', 'client event')
entries = [
    Entry(client=client, event=asyncio.Event()),
    Entry(client=janitor, event=asyncio.Event())
]

loop = asyncio.get_event_loop()

@client.command()
async def track(ctx, channels: commands.Greedy[discord.TextChannel] = tuple()):
    global tracked_channels
    tracked_channels = channels

@client.event
async def on_reaction_add(reaction, user):
    if reaction.message.channel in tracked_channels and reaction.emoji == '\U0001f983' and user != client.user:
        await reaction.remove(user)
        await user.create_dm()
        await user.dm_channel.send(embed=discord.Embed(title="HAPPY ONE DAY BIRTHDAY, JACOB!! :partying_face:", colour=0xE94545, description=f"Happy birthday to you.\nHappy birthday to you.\nHappy birthday dear Jacob.\nHappy birthday to you.\n:turkey:"))


not_dead = ['jl', 'jiawei', 'weiwei']

@client.command()
async def party(ctx):
    await ctx.author.create_dm()
    embed = discord.Embed(title="Host a Party :partying_face:", colour=0xb1a3ff, description="Do you want to hold a funeral or a birthday party?")
    embed.add_field(name='Funeral', value="Please react with :skull: if you would like to host a funeral.")
    embed.add_field(name='Birthday Party', value="Please react with :birthday: if you would like to host a birthday party.")

    dm = ctx.author.dm_channel
    party_type = await dm.send(embed=embed)
    await party_type.add_reaction('\U0001f480')
    await party_type.add_reaction('\U0001f382')

    type = None
    def check(reaction, user):
        return (reaction.emoji == '\U0001f480' or '\U0001f382') and user == ctx.author and reaction.message == party_type

    reaction, user = await client.wait_for('reaction_add', check=check)
    if reaction.emoji == '\U0001f480':
        type = 'funeral'
    elif reaction.emoji == '\U0001f382':
        type = 'birthday party'
    await dm.send(embed=discord.Embed(colour=0xb1a3ff, description="Who is this party for?"))

    def message_check(message):
        return (message.content != "") and message.author == ctx.author
    person = await client.wait_for('message', check=message_check)
    if type == 'funeral' and any(alive in person.content.lower() for alive in not_dead):
        await dm.send(embed=discord.Embed(colour=0x9c0000, description="That person is still alive. :angry:"))
        return
    for guild in client.guilds:
        for channel in guild.text_channels:
            try:
                await channel.send(embed=discord.Embed(title=f"We are holding a {type} for {person.content}! :partying_face:", colour=0xb1a3ff))
            except:
                continue
    await dm.send(embed=discord.Embed(title=f"We are holding a {type} for {person.content}! :partying_face:", colour=0xb1a3ff))


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
