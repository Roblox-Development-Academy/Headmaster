import asyncio

import discord

import common
from wizards.stage_type import StageType
from bot import EMOJIS, EMBED_COLORS

# TODO - Create a multistage type that allows both reactions and text


async def process_text_wizards(msg):
    for channelId, wizard in Wizard.text_wizards.items():
        if channelId == msg.channel.id:
            if await wizard.stages[wizard.stage].respond(wizard, msg):
                Wizard.text_wizards.pop(channelId)


async def process_reaction_wizards(reaction, user):
    for messageId, wizard in Wizard.reaction_wizards.items():
        if messageId == reaction.message.id:
            if await wizard.stages[wizard.stage].respond(wizard, reaction, user):
                Wizard.reaction_wizards.pop(messageId)


class Wizard:
    text_wizards = {}  # Dictionary of channel IDs to Wizards
    reaction_wizards = {}  # Dictionary of message Ids to Wizards

    @staticmethod
    async def __exit(wizard):
        embed = discord.Embed(title=f"{EMOJIS['error']} Timed Out", colour=EMBED_COLORS["error"],
                              description="You did not respond in time and the wizard timed out. Please restart.")

        await wizard.messages[-1].edit(embed)

    def __init__(self, stages=None, exit_func=__exit):
        self.stage = 0  # The current stage of the wizard
        self.stages = stages or []  # List of the Stage objects in order
        self.messages = []  # All the bot messages sent
        self.responses = {}  # Dictionary that could be be used to store anything from responses
        self.exit = exit_func  # A coroutine for exit behavior

    async def __timeout(self, wizard_dict):
        timeout = self.stages[self.stage].timeout
        if timeout > 0:
            await asyncio.sleep(timeout)
            for key, wizard in wizard_dict.items():
                if wizard == self:
                    wizard_dict.pop(key)
                    await self.exit(self)

    async def send(self, to_edit=None, channel=None, stage=None):
        """
        Sends the current stage of the Wizard's message. Defaults to editing the last message sent.
        :param to_edit: The message to replace with the Wizard's new message
        :param channel: The channel to send the message in
        :param stage: The stage of the Wizard to send. Defaults to current
        """
        # TODO - Schedule time-out with exit() function - maybe with python module sched or cogs and discord.py's tasks
        self.stage = stage or self.stage
        stage = self.stages[self.stage]
        if not channel:
            to_edit = to_edit or self.messages[-1]
            message = await common.unpack(stage.messages[0], to_edit.edit)
            if stage.type == StageType.REACTION:
                self.reaction_wizards[message.id] = self
                await self.__timeout(self.reaction_wizards)
                return
        else:
            for message in stage.messages:
                await self.messages.append(common.unpack(message, channel.send))
            if stage.type == StageType.REACTION:
                self.reaction_wizards[self.messages[-1].id] = self
                await self.__timeout(self.reaction_wizards)
                return
        if stage.type == StageType.TEXT:
            self.text_wizards[(channel or to_edit.channel).id] = self
            await self.__timeout(self.text_wizards)
