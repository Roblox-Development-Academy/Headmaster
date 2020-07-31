import yaml
import copy
import re
from typing import Union, List, Dict, Any
from datetime import datetime

import discord


class MessageNode:
    send_args = ('content', 'tts', 'embed', 'file', 'files', 'nonce', 'delete_after', 'allowed_mentions')

    def __init__(self, **kwargs):
        self.args: Dict[str, Any] = {}
        self.options: Dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in MessageNode.send_args:
                self.args[key] = value
            elif key == "timestamp":
                if self.args.get('embed'):
                    self.args['embed'].timestamp = value
                else:
                    kwargs['embed'].timestamp = value
            else:
                self.options[key] = value

    @classmethod
    async def from_message(cls, message: discord.Message):
        serialized = {'content': message.content, 'tts': message.tts, 'nonce': message.nonce,
                      'embed': message.embeds[0] if message.embeds else None}
        if message.embeds and isinstance(message.embeds[0].timestamp, datetime):
            serialized['timestamp'] = message.embeds[0].timestamp

        if message.attachments:
            files = [await attachment.to_file() for attachment in message.attachments]

            if len(files) > 1:
                serialized['files'] = files
            else:
                serialized['file'] = files[0]

        return cls(**serialized)

    @classmethod
    def from_str(cls, serialized: str):
        return cls(content=serialized)

    @classmethod
    def from_dict(cls, serialized: dict):
        embed = serialized.get('embed')
        if embed:
            e = discord.Embed.Empty
            footer = embed.get('footer')
            image = embed.get('image')
            thumbnail = embed.get('thumbnail')
            author = embed.get('author')
            fields = embed.get('fields')
            colour = embed.get('colour') or embed.get('color') or e
            colour = discord.Colour(colour if not isinstance(colour, str) else int(colour, 16)) if colour != e else e
            serialized['embed'] = discord.Embed(title=embed.get('title', e), type=embed.get('type'), colour=colour,
                                                description=embed.get('description', e), url=embed.get('url', e))
            embed = serialized['embed']
            if footer:
                embed.set_footer(**footer)
            if image:
                embed.set_image(url=image if isinstance(image, str) else image.get('url'))
            if thumbnail:
                embed.set_thumbnail(url=thumbnail if isinstance(thumbnail, str) else thumbnail.get('url'))
            if author:
                embed.set_author(**author)
            if fields:
                for field in fields:
                    if field.get('index') is None:
                        embed.add_field(**field)
                    else:
                        embed.insert_field_at(**field)

        file = serialized.get('file')
        files = serialized.get('files')

        def deserialize_file(serialized_file: Union[str, dict]) -> discord.File:
            if isinstance(serialized_file, str):
                return discord.File(serialized_file)
            else:
                return discord.File(**serialized_file)

        if file:
            serialized['file'] = deserialize_file(file)
        elif files:
            serialized['files'] = [deserialize_file(x) for x in files]

        allowed_mentions = serialized.get('allowed_mentions')
        if allowed_mentions:
            serialized['allowed_mentions'] = discord.AllowedMentions(**allowed_mentions)
        return cls(**serialized)

    def replace(self, **kwargs):
        if len(kwargs) == 0:
            return self
        clone = copy.deepcopy(self)
        content = clone.args.get('content')
        if content:
            clone.args['content'] = LangManager.replace(content, **kwargs)
        embed: discord.Embed = clone.args.get('embed')
        if embed:
            if embed.title:
                embed.title = LangManager.replace(embed.title, **kwargs)
            if embed.description:
                embed.description = LangManager.replace(embed.description, **kwargs)
            if embed.url:
                embed.url = LangManager.replace(embed.url, **kwargs)
            if embed.footer:
                embed.set_footer(text=LangManager.replace(embed.footer.text, **kwargs),
                                 icon_url=LangManager.replace(embed.footer.icon_url, **kwargs))
            if embed.author:
                embed.set_author(name=LangManager.replace(embed.author.name, **kwargs),
                                 url=LangManager.replace(embed.author.url, **kwargs),
                                 icon_url=LangManager.replace(embed.author.icon_url, **kwargs))
            if embed.image:
                embed.set_image(url=LangManager.replace(embed.image.url, **kwargs))
            if embed.thumbnail:
                embed.set_thumbnail(url=LangManager.replace(embed.thumbnail.url, **kwargs))
            for i, field in enumerate(embed.fields):
                embed.set_field_at(i, name=LangManager.replace(field.name, **kwargs),
                                   value=LangManager.replace(field.value, **kwargs), inline=field.inline)
        return clone

    async def send(self, to, message_list=None, **placeholders):
        if len(self.args) == 0:
            return message_list
        if isinstance(to, discord.abc.Messageable):
            msg = await to.send(**self.replace(**placeholders).args)

            reactions = self.options.get('reactions')
            if reactions:
                for reaction in reactions:
                    if isinstance(reaction, int):
                        reaction = LangManager.bot.get_emoji(reaction)
                    await msg.add_reaction(reaction)
            if message_list is not None:
                message_list.append(msg)
                return message_list
            else:
                return msg
        else:
            for element in to:
                await self.send(element, message_list=message_list, **placeholders)
            return message_list

    async def edit(self, message, **placeholders):
        msg = await message.edit(**self.replace(**placeholders).args)

        reactions = self.args.get('reactions')
        if reactions:
            for reaction in reactions:
                await msg.add_reaction(reaction)
        return msg


class MessageListNode:
    def __init__(self, *nodes: MessageNode):
        self.nodes: List[MessageNode] = list(nodes)

    @classmethod
    def from_list(cls, serialized: list):
        return cls(*((MessageNode.from_dict(msg) if isinstance(msg, dict) else MessageNode.from_str(msg)) for msg in
                     serialized))

    @classmethod
    def from_str(cls, serialized: str):
        return cls(MessageNode.from_str(serialized))

    def replace(self, **kwargs):
        return MessageListNode(*(node.replace(**kwargs) for node in self.nodes))

    async def send(self, to, **kwargs):
        results = []
        for node in self.nodes:
            await node.send(to, results, **kwargs)
        return results

    async def edit(self, *messages, **placeholders):
        results = []
        for to_edit, node in zip(messages, self.nodes):
            if isinstance(to_edit, list):
                for msg in to_edit:
                    results.append(await node.edit(msg, **placeholders))
            else:
                results.append(await node.edit(to_edit, **placeholders))
        return results


class LangManager:
    empty = MessageListNode()
    matcher = re.compile(r'%([\w._]+)%')
    global_placeholders = {}
    bot = None

    @staticmethod
    def __index_strings(config: dict, final_dict: dict = None, index: str = ''):
        if final_dict is None:
            final_dict = {}
        for key, value in config.items():
            if isinstance(value, dict):
                LangManager.__index_strings(value, final_dict, index + "." + key if index != '' else key)
            else:
                final_dict[index + '.' + key if index != '' else key] = str(value)
        return final_dict

    @staticmethod
    def replace(to_replace: str, **placeholders):
        if not placeholders:
            placeholders = LangManager.global_placeholders
        try:
            match = LangManager.matcher.search(to_replace)
        except TypeError:
            return to_replace
        while match is not None:
            value = placeholders.get(match.group(1))
            span = match.span()
            if value is not None:
                to_replace = to_replace[:span[0]] + value + to_replace[span[1]:]
                match = LangManager.matcher.search(to_replace, span[0])
            else:
                match = LangManager.matcher.search(to_replace, span[1])
        return to_replace

    def __init__(self, *yaml_files, bot=None):
        self.nodes = {}
        self.files = set(yaml_files)
        if not LangManager.bot:
            LangManager.bot = bot

        self.load()

    def load(self, *yaml_files, clear=False):
        if not yaml_files:
            yaml_files = self.files
        if clear:
            self.nodes.clear()
            LangManager.global_placeholders.clear()
        self.files.update(yaml_files)

        def globally_replace(config):
            for key, value in (enumerate(config) if isinstance(config, list) else config.items()):
                if isinstance(value, str):
                    config[key] = LangManager.replace(value)
                elif isinstance(value, list) or isinstance(value, dict):
                    globally_replace(value)

        def index_messages(config: dict, index: str = ''):
            for key, value in config.items():
                key = str(key)
                if isinstance(value, list):
                    globally_replace(value)
                    self.nodes[index + "." + key if index != '' else key] = MessageListNode.from_list(value)
                elif isinstance(value, dict):
                    index_messages(value, index + "." + key if index != '' else key)
                elif isinstance(value, str):
                    self.nodes[index + "." + key if index != '' else key] = MessageListNode.from_str(value)

        for yaml_file in yaml_files:
            with open(yaml_file, encoding='utf-8') as f:
                config_dict = yaml.load(f, Loader=yaml.FullLoader)
                global_placeholders = config_dict.get('global_placeholders')
                if global_placeholders:
                    LangManager.__index_strings(global_placeholders, LangManager.global_placeholders)
                index_messages(config_dict['messages'])

    def get(self, index: str):
        return self.nodes.get(index, LangManager.empty)
