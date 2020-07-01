import asyncio

import discord

import errors
from bot import client
from main import in_prompt


def parameters(*args, **kwargs):
    return args, kwargs


def unpack(packed_parameters, coroutine):
    return coroutine(*packed_parameters[0], **packed_parameters[1])


async def prompt(channel: discord.TextChannel, user: discord.User, prompt_msg=None, timeout=300,
                 **kwargs) -> discord.Message:
    """
    Prompts the specified user for a text response

    :param user: The specific user to prompt
    :param channel: The channel to send the prompt in
    :param prompt_msg: The message to edit if error or the message node to send
    :param timeout: How many seconds before timeout
    :return: The user's response
    """
    if not isinstance(prompt_msg, discord.Message):
        prompt_msg = await prompt_msg.send(**kwargs)

    def check(m):
        return m.author == user and m.channel == channel

    in_prompt[user.id] = prompt_msg.jump_url
    try:
        msg = await client.wait_for("message", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        in_prompt.pop(user.id)
        raise errors.PromptTimeout("The prompt has timed out", prompt_msg)

    if msg.content.lower() == "cancel":
        in_prompt.pop(user.id)
        raise errors.PromptCancelled("The prompt was cancelled", prompt_msg)

    in_prompt.pop(user.id)
    return msg
