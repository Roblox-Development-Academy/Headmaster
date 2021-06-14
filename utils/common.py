from typing import Union, Callable, Tuple, Awaitable, Any
import asyncio
import re
from datetime import datetime, timedelta

import errors
import events
from bot import *
from cogs import errorhandler
from utils.language import MessageNode, MessageListNode


async def __do_nothing():
    pass


interval_matcher = re.compile(r'^((?P<days>[.\d]+?)d)? *'
                              r'((?P<hours>[.\d]+?)h)? *'
                              r'((?P<minutes>[.\d]+?)m)? *'
                              r'((?P<seconds>[.\d]+?)s)?$')


def parse_interval(time: str, minimum: timedelta = timedelta(seconds=0), maximum: timedelta = timedelta(days=30)):
    parts = interval_matcher.match(time)
    # assert parts is not None, """Could not parse any time information from '{}'.
    # Examples of valid strings: '8h', '2d 8h 5m 2s', '2m4.3s'""".format(time)
    if parts is None:
        return None
    time_params = {name: float(param) for name, param in parts.groupdict().items() if param}
    result = timedelta(**time_params)
    try:
        if minimum <= result <= maximum:
            return result
    except TypeError:
        return None
    raise OverflowError


def td_format(td_object: timedelta) -> str:
    seconds = int(td_object.total_seconds())
    periods = {
        'day': 60*60*24,
        'hour': 60*60,
        'minute': 60,
        'second': 1
    }

    strings = []
    for period_name, period_seconds in periods.items():
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append(f"{period_value} {period_name}{has_s}")
    return ", ".join(strings)


async def prompt_reaction(msg: Union[discord.Message, MessageNode, MessageListNode], user: discord.User = None, *args,
                          timeout=300, allowed_emojis=None, remove_other_reactions=True,
                          **kwargs) -> Tuple[discord.Reaction, discord.User]:
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
        raise errors.PromptTimeout("The prompt has timed out", msg)
    finally:
        in_prompt.pop(user.id, None)
    return response, responder


async def prompt(channel: discord.TextChannel, user: discord.User,
                 prompt_msg: Union[discord.Message, MessageNode, MessageListNode], timeout=300, back=None,
                 can_skip=False, check: Callable = None, **kwargs) -> discord.Message:
    """
    Prompts the specified user for a text response

    :param user: The specific user to prompt
    :param channel: The channel to send the prompt in
    :param prompt_msg: The message to edit if error or the message node to send
    :param timeout: How many seconds before timeout
    :param back: A coroutine to be called if 'back' is an allowed response
    :param can_skip: Whether this prompt is skippable (must be handled)
    :param check: Your own check for messages
    :return: The user's response
    """
    if not isinstance(prompt_msg, discord.Message):
        prompt_msg = await prompt_msg.send(channel, **kwargs)

    if not check:
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
                await errorhandler.process(channel, errors.PromptSkipped("This prompt cannot be skipped", msg))
            elif msg.content.lower() == "back":
                if back:
                    raise errors.PreviousPrompt("Went back to previous prompt", msg, back)
                await errorhandler.process(channel, errors.PreviousPrompt("Cannot go back to previous prompt", channel))
            elif (await client.get_context(msg)).valid:
                pass
            else:
                break
    except asyncio.TimeoutError:
        raise errors.PromptTimeout("The prompt has timed out.", prompt_msg)
    finally:
        in_prompt.pop(user.id, None)

    if msg.content.lower() in ('cancel', 'cancel.'):
        raise errors.PromptCancelled("The prompt was cancelled.", prompt_msg)
    return msg


async def prompt_date(channel: discord.TextChannel, user: discord.User,
                      prompt_msg: Union[discord.Message, MessageNode, MessageListNode], timeout=300,
                      **kwargs) -> datetime:
    def msg_check(m):
        return m.author == user and m.channel == channel and m.content and \
               m.content.lower() in ('skip', 'back', 'cancel', 'cancel.')

    def date_check(user_id, _=None):
        return user_id == user.id

    date_fut = asyncio.get_event_loop().create_future()
    wait_date = asyncio.create_task(events.date_selected.wait(check=date_check, future=date_fut))
    wait_msg = asyncio.create_task(prompt(channel, user, prompt_msg, timeout, check=msg_check,
                                          url=f"{WEB_URL}/date-select/?user-id={user.id}", **kwargs))
    for fut in asyncio.as_completed([wait_date, wait_msg]):
        try:
            result = await fut
            return None if result is None else result[1]
        except errors.PromptError:  # Means the message was first
            events.date_selected.signals.pop(date_fut)
            raise
        finally:
            in_prompt.pop(user.id, None)


async def prompt_wait(channel: discord.TextChannel, user: discord.User,
                      prompt_msg: Union[discord.Message, MessageNode, MessageListNode], coro: Awaitable, timeout=300,
                      on_msg: Awaitable = __do_nothing(), **kwargs) -> Any:
    def msg_check(m):
        return m.author == user and m.channel == channel and m.content and \
               m.content.lower() in ('skip', 'back', 'cancel', 'cancel.')

    wait_other = asyncio.create_task(coro)
    wait_msg = asyncio.create_task(prompt(channel, user, prompt_msg, timeout, check=msg_check,
                                          url=f"{WEB_URL}/date-select/?user-id={user.id}", **kwargs))
    for fut in asyncio.as_completed([wait_other, wait_msg]):
        try:
            result = await fut
            return result
        except errors.PromptError:  # Means the message was first
            await on_msg
            raise
        finally:
            in_prompt.pop(user.id, None)
