import psycopg2

from bot import *
from cogs import errorhandler
from language import LangManager
from copy import deepcopy


class Admin(commands.Cog):

    @staticmethod
    def __add_ignored_channels(rows):
        try:
            database.cursor.executemany(
                """
                INSERT INTO ignored_channels (id, guild_id) VALUES (%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                rows
            )
            database.connection.commit()
        except psycopg2.DatabaseError:
            database.connect()
            Admin.__add_ignored_channels(rows)

    @commands.command(aliases=["findprefix", "showprefix"])
    @commands.guild_only()
    async def getprefix(self, ctx):
        await lang.get('prefix.get').send(ctx, prefix=get_prefix(ctx.guild.id))

    @commands.command(restisraw=True)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def setprefix(self, ctx, prefix=None):
        if prefix is None:
            await lang.get('prefix.info').send(ctx, prefix=get_prefix(ctx.guild.id))
            return

        prefix_length = len(prefix)

        if prefix_length > 15:
            await lang.get('error.prefix.invalid').send(ctx, prefix=prefix, prefix_length=prefix_length)
            return

        database.update(
            """
            INSERT INTO guilds (id, prefix) VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE SET prefix = EXCLUDED.prefix
            """,
            (ctx.guild.id, prefix)
        )

        await lang.get('prefix.success').send(ctx, prefix=prefix, client=client.user.mention)

    @getprefix.error
    @setprefix.error
    async def prefix_cmd_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await lang.get('error.prefix.server_only').send(ctx)
        else:
            await errorhandler.process(ctx, error)

    """
    Don't worry; the command only takes channel arguments for the channels in the current server.
    """

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def ignore(self, ctx, sub: str = None, channels: commands.Greedy[discord.TextChannel] = None):
        give_example = True
        color = "%color.info%"
        msg = ""
        example = None
        if sub:
            if sub.lower() == "add" and channels:
                rows = [(str(channel.id), str(ctx.guild.id)) for channel in channels]
                # args_str = database.cursor.mogrify("(%s,%s)", (str(ctx.channel.id), str(ctx.guild.id)))  # testing
                # args_str = ",".join(database.cursor.mogrify("(%s,%s)", (str(channel.id), str(ctx.guild.id))) for
                # channel in channels)
                # logger.debug("Psycopg2's mogrified arg_str: " + str(args_str))
                Admin.__add_ignored_channels(rows)
                msg = "**The specified channels are now ignored!**\n\n"
                give_example = False
                color = "%color.success%"
            elif sub.lower() in ("remove", "delete") and channels:
                database.update(
                    f"""
                    DELETE FROM ignored_channels
                    WHERE id IN ({",".join(str(channel.id) for channel in channels)})
                    """
                )
                msg = "**The specified channels are not ignored anymore!**\n\n"
                give_example = False
                color = "%color.success%"
        ignore_node = deepcopy(lang.get('ignore'))
        if give_example:
            guild_channels = ctx.guild.channels
            num_channels = len(guild_channels)
            example = " ".join(
                guild_channels[i].mention if num_channels > i else "#channel" + str(i) for i in range(3))
        else:
            ignore_node.nodes[0].args['embed'].remove_field(0)

        ignored_channels = get_ignored_channels(ctx.guild.id)
        ignored_channels_list = ""
        if len(ignored_channels) != 0:
            for channel in ignored_channels:
                try:
                    ignored_channels_list += f"{ctx.guild.get_channel(channel[0]).mention}\n"
                except AttributeError:
                    database.update(
                        """
                        DELETE FROM ignored_channels
                        WHERE id = %s
                        """,
                        (channel[0],)
                    )
        else:
            ignored_channels_list = "*There are no ignored channels.*"
        ignore_node = ignore_node.replace(message=msg, prefix=get_prefix(ctx.guild.id), channels=ignored_channels_list, example=example)
        ignore_node.nodes[0].args['embed'].color = discord.Color(int(LangManager.replace(color), 16))
        await ignore_node.send(ctx)
