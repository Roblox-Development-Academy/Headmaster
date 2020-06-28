from bot import *
import errors


async def process_errors(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title=f"{EMOJIS['error']} No permission to use this command",
                              colour=EMBED_COLORS['error'],
                              description=error.args[0])

        await ctx.send(embed=embed)
    elif isinstance(error, commands.NoPrivateMessage):
        embed = discord.Embed(title=f"{EMOJIS['error']} Server-only command", colour=EMBED_COLORS['error'],
                              description=f"You can only use this command in a server.")

        await ctx.send(embed=embed)
    elif isinstance(error, errors.PromptCancelled):
        embed = discord.Embed(title="Setup Cancelled", colour=EMBED_COLORS['error'],
                              description="You have cancelled the setup. Please re-execute the command "
                                          "again to restart the setup.")
        await error.args[0].edit(embed=embed)
    elif isinstance(error, errors.PromptTimeout):
        embed = discord.Embed(title=f"{EMOJIS['error']} Timed Out", colour=EMBED_COLORS['error'],
                              description="You have waited too long. The prompt timed out. Please re-execute "
                                          "the command to restart.")
        await error.args[0].edit(embed=embed)
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        raise error


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    @client.event
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, "on_error"):
            return
        await process_errors(ctx, error)
