from bot import *
import errors


async def process(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await lang.get('error.missing_permissions').send(ctx, description=error.args[0])
    elif isinstance(error, commands.NoPrivateMessage):
        await lang.get('error.server_only').send(ctx)
    elif isinstance(error, errors.PromptSkipped):
        await error.args[1].delete()
        await lang.get('error.prompt_skip').send(ctx)
    elif isinstance(error, errors.PromptCancelled):
        await lang.get('error.prompt_cancel').edit(error.args[1])
    elif isinstance(error, errors.PromptTimeout):
        await lang.get('error.prompt_timeout').edit(error.args[1])
    elif isinstance(error, errors.PreviousPrompt):
        try:
            await error.args[2]
        except IndexError:
            await lang.get('error.previous_prompt').send(error.args[1])
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, commands.errors.CommandNotFound):
        pass
    else:
        raise error


class ErrorHandler(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, "on_error"):
            return
        await process(ctx, error)
