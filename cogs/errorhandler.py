from bot import *
import errors


async def process_errors(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await lang.get('error.missing_permissions').send(ctx, description=error.args[0])
    elif isinstance(error, commands.NoPrivateMessage):
        await lang.get('error.server_only').send(ctx)
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
