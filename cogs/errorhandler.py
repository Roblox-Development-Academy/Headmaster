from bot import *
import errors


async def process_errors(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await lang.get('error.missing_permissions').send(ctx, description=error.args[0])
    elif isinstance(error, commands.NoPrivateMessage):
        await lang.get('error.server_only').send(ctx)
    elif isinstance(error, errors.PromptCancelled):
        await lang.get('error.prompt_cancel').edit(error.args[0])
    elif isinstance(error, errors.PromptTimeout):
        await lang.get('error.prompt_timeout').edit(error.args[0])
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
