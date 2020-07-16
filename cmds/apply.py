from bot import *
from common import prompt_reaction, prompt
from language import MessageNode


@commands.command()
async def apply(ctx):
    message = (await lang.get('teacher_application.initiate').send(ctx))[0]
    await prompt_reaction(message, ctx.author, allowed_emojis=lang.global_placeholders.get('emoji.confirm'))
    await lang.get('teacher_application.start').send(ctx)

    prompt_message = (await lang.get('teacher_application.dm_message').send(ctx.author))[0]
    user_dm = ctx.author.dm_channel
    gotcha_emote = lang.global_placeholders.get('emoji.gotcha')

    channel = client.get_channel(728753615031763005)  # Change this to the channel we'll be using.

    messages = []
    while True:
        message = await prompt(user_dm, ctx.author, prompt_message)

        if message.content.lower() in ('done', 'done.'):
            break

        messages.append(message.id)

        await message.add_reaction(gotcha_emote)
    in_prompt.pop(ctx.author.id)
    await lang.get('teacher_application.complete').send(user_dm)
    await lang.get('teacher_application.ta_content').send(channel, user=str(ctx.author),
                                                          user_mention=ctx.author.mention)
    for id in messages:
        try:
            message = await user_dm.fetch_message(id)
        except discord.errors.NotFound:
            continue
        copy = await MessageNode.from_message(message)
        await copy.send(channel)
    await lang.get('teacher_application.end').send(channel, user=str(ctx.author))


def setup(bot):
    bot.add_command(apply)
