from bot import *


@client.command()
async def apply(ctx):
    message = await lang.get('teacher_application.1').send(ctx)
    confirm_emoji = EMOJIS['confirm']
    message.add_reaction(f"{confirm_emoji}")

    _, reaction = client.wait_for("reaction_add")
    pass
