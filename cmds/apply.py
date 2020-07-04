from bot import *
from common import prompt_reaction, prompt


@commands.command()
async def apply(ctx):
    message = (await lang.get('teacher_application.initiate').send(ctx))[0]
    await prompt_reaction(message, ctx.author, allowed_emojis=lang.global_placeholders.get('emoji.confirm'))
    await lang.get('teacher_application.start').send(ctx)

    prompt_message = (await lang.get('teacher_application.dm_message').send(ctx.author))[0]
    user_dm = ctx.author.dm_channel
    gotcha_emote = lang.global_placeholders.get('emoji.gotcha')

    channel = client.get_channel(728753615031763005)
    channel = client.get_user(450375444450115585)
    while True:
        message = await prompt(user_dm, ctx.author, prompt_message)

        if message.content.lower() in ('done', 'done.'):
            await lang.get('teacher_application.ta_content.submit').send(channel, user=str(ctx.author), user_mention=ctx.author.mention)
            break

        await lang.get('teacher_application.ta_content.log').send(channel, user=str(ctx.author), user_mention=ctx.author.mention, amount=str(len(message.attachments)), content=message.content)

        files = []
        if len(message.attachments) > 0:
            for attachment in message.attachments:
                files.append(await attachment.to_file())
            await channel.send(files=files)

        await message.add_reaction(gotcha_emote)
    await lang.get('teacher_application.complete').send(user_dm)


def setup(bot):
    bot.add_command(apply)
