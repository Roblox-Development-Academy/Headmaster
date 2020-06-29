import asyncio

import discord

import errors
from bot import client, lang


def parameters(*args, **kwargs):
    return args, kwargs


def unpack(packed_parameters, coroutine):
    return coroutine(*packed_parameters[0], **packed_parameters[1])


async def prompt(channel: discord.TextChannel, user: discord.User, *args, prompt_msg: discord.Message = None,
                 timeout=300, **kwargs) -> discord.Message:
    """
    Prompts the specified user for a text response

    :param user: The specific user to prompt
    :param channel: The channel to send the prompt in
    :param prompt_msg: The message object to edit if error
    :param timeout: How many seconds before timeout
    :return: The user's response
    """
    # TODO - Add the user to a dictionary whose commands are not seen in the channel due to being in the prompt
    if not prompt_msg:
        prompt_msg = (await lang.get('prompt').send(channel, args=*args, kwargs=**kwargs))[0]

    def check(m):
        return m.author == user and m.channel == channel

    msg = None
    try:
        msg = await client.wait_for("message", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        raise errors.PromptTimeout("The prompt has timed out", prompt_msg)

    if msg.content.lower() == "cancel":
        raise errors.PromptCancelled("The prompt was cancelled", prompt_msg)

    return msg