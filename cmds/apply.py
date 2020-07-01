from bot import *


@commands.command()
async def apply(ctx):
    message = await lang.get('teacher_application.1').send(ctx)
    confirm_emoji = EMOJIS['confirm']
    message.add_reaction(f"{confirm_emoji}")

    _, reaction = client.wait_for("reaction_add")
    pass


def setup(bot):
    bot.add_command(apply)
