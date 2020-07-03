import asyncio

import errors
from bot import *
from cogs import errorhandler


def parameters(*args, **kwargs):
    return args, kwargs


def unpack(packed_parameters, coroutine):
    return coroutine(*packed_parameters[0], **packed_parameters[1])


async def prompt_reaction(msg: discord.Message, user: discord.User = None, *args, timeout=300, allowed_emojis=None,
                          remove_other_reactions=True, **kwargs):
    if not isinstance(msg, discord.Message):
        msg = await msg.send(*args, **kwargs)
        if isinstance(msg, list):
            msg = msg[-1]

    def check(reaction, reactor):
        return (reaction.message.id == msg.id) and (not user or user.id == reactor.id)

    if user:
        in_prompt[user.id] = msg.jump_url
    try:
        while True:
            response, responder = await client.wait_for('reaction_add', check=check, timeout=timeout)

            if not allowed_emojis or (response.emoji in allowed_emojis):
                break
            if remove_other_reactions:
                try:
                    await response.remove(responder)
                except discord.errors.Forbidden:
                    await lang.get('error.invalid_reaction').send(msg.channel)
    except asyncio.TimeoutError:
        in_prompt.pop(user.id)
        raise errors.PromptTimeout("The prompt has timed out", msg)
    return response, responder


async def prompt(channel: discord.TextChannel, user: discord.User, prompt_msg, timeout=300,
                 back=None, can_skip=False, **kwargs) -> discord.Message:
    """
    Prompts the specified user for a text response

    :param user: The specific user to prompt
    :param channel: The channel to send the prompt in
    :param prompt_msg: The message to edit if error or the message node to send
    :param timeout: How many seconds before timeout
    :param back: A coroutine to be called if 'back' is an allowed response
    :param can_skip: Whether this prompt is skippable (must be handled)
    :return: The user's response
    """
    if not isinstance(prompt_msg, discord.Message):
        prompt_msg = await prompt_msg.send(channel, **kwargs)

    def check(m):
        return m.author == user and m.channel == channel

    try:
        in_prompt[user.id] = prompt_msg.jump_url
    except AttributeError:
        in_prompt[user.id] = prompt_msg[0].jump_url
    try:
        while True:
            msg = await client.wait_for("message", check=check, timeout=timeout)
            if msg.content.lower() == "skip":
                if can_skip:
                    raise errors.PromptSkipped("The skipping wasn't handled", msg)
                else:
                    await errorhandler.process(channel,
                                               errors.PromptSkipped("This prompt cannot be skipped", msg))
            elif msg.content.lower() == "back":
                if back:
                    raise errors.PreviousPrompt("Went back to previous prompt", msg, back)
                await errorhandler.process(channel, errors.PreviousPrompt("Cannot go back to previous prompt",
                                                                          channel))
            else:
                break
    except asyncio.TimeoutError:
        in_prompt.pop(user.id)
        raise errors.PromptTimeout("The prompt has timed out", prompt_msg)

    if msg.content.lower() in ['cancel', 'cancel.']:
        in_prompt.pop(user.id)
        raise errors.PromptCancelled("The prompt was cancelled", prompt_msg)
    return msg
