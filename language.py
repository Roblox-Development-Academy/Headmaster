import yaml
import copy
from typing import Union

import discord


class MessageNode:
    send_args = ('content', 'tts', 'embed', 'file', 'files', 'nonce', 'delete_after', 'allowed_mentions')

    def __init__(self, **kwargs):
        self.args = {}
        self.options = {}
        for key, value in kwargs.items():
            if key in MessageNode.send_args:
                self.args[key] = value
            elif key == "timestamp":
                embed = kwargs['embed']
                embed.timestamp = value
            else:
                self.options[key] = value

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
            colour = discord.Colour(colour if not isinstance(colour, str) else int(colour, 16))
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

    @staticmethod
    def __replace(text, placeholders):
        if not isinstance(text, str):
            return text
        for key, value in placeholders.items():
            text = text.replace(f"%{key}%", str(value))
        return text

    def replace(self, **kwargs):
        if len(kwargs) == 0:
            return self
        clone = copy.deepcopy(self)
        content = clone.args.get('content')
        if content:
            clone.args['content'] = MessageNode.__replace(content, kwargs)
        embed: discord.Embed = clone.args.get('embed')
        if embed:
            embed.title = MessageNode.__replace(embed.title, kwargs)
            embed.description = MessageNode.__replace(embed.description, kwargs)
            embed.url = MessageNode.__replace(embed.url, kwargs)
            if embed.footer:
                embed.set_footer(text=MessageNode.__replace(embed.footer.text, kwargs),
                                 icon_url=MessageNode.__replace(embed.footer.icon_url, kwargs))
            if embed.author:
                embed.set_author(name=MessageNode.__replace(embed.author.name, kwargs),
                                 url=MessageNode.__replace(embed.author.url, kwargs),
                                 icon_url=MessageNode.__replace(embed.author.icon_url, kwargs))
            if embed.image:
                embed.set_image(url=MessageNode.__replace(embed.image.url, kwargs))
            if embed.thumbnail:
                embed.set_thumbnail(url=MessageNode.__replace(embed.thumbnail.url, kwargs))
            for i, field in enumerate(embed.fields):
                embed.set_field_at(i, name=MessageNode.__replace(field.name, kwargs),
                                   value=MessageNode.__replace(field.value, kwargs))
        return clone

    async def send(self, to, **placeholders):
        try:
            return await to.send(**self.replace(**placeholders).args)
        except AttributeError:
            print("MessageNode attribute error")
            for to_message in to:
                return await to_message.send(**self.replace(**placeholders).args)

    async def edit(self, message, **placeholders):
        return await message.edit(**self.replace(**placeholders).args)


class MessageListNode:
    def __init__(self, *nodes: MessageNode):
        self.nodes = nodes

    @classmethod
    def from_list(cls, serialized: list):
        return cls(*((MessageNode.from_dict(msg) if isinstance(msg, dict) else MessageNode.from_str(msg)) for msg in
                     serialized))

    @classmethod
    def from_str(cls, serialized: str):
        return cls(MessageNode.from_str(serialized))

    async def send(self, *args, **kwargs):
        results = []
        for node in self.nodes:
            results.append(await node.send(*args, **kwargs))
        return results

    async def edit(self, *messages, **placeholders):
        results = []
        for to_edit, node in zip(messages, self.nodes):
            results.append(await node.edit(to_edit, **placeholders))
        return results


class LangManager:
    empty = MessageListNode()

    @staticmethod
    def __index_strings(config: dict, final_dict: dict = None, index: str = ''):
        if final_dict is None:
            final_dict = {}
        for key, value in config.items():
            if isinstance(value, dict):
                LangManager.__index_strings(value, final_dict, index + "." + key if index != '' else key)
            else:
                final_dict[f"%{index + '.' + key if index != '' else key}%"] = str(value)
        return final_dict

    def __init__(self, *yaml_files):
        self.nodes = {}
        self.placeholders = {}
        self.files = set(yaml_files)

        self.load()

    def load(self, *yaml_files, clear=False):
        if not yaml_files:
            yaml_files = self.files
        if clear:
            self.nodes.clear()
            self.placeholders.clear()
        self.files.update(yaml_files)

        def globally_replace(config):
            for key, value in (config.items() if isinstance(config, dict) else enumerate(config)):
                if isinstance(value, str):
                    for replace, replace_with in self.placeholders.items():
                        value = value.replace(replace, replace_with)
                        config[key] = value
                elif isinstance(value, list) or isinstance(value, dict):
                    globally_replace(value)

        def index_messages(config: dict, index: str = ''):
            for key, value in config.items():
                if isinstance(value, list):
                    globally_replace(value)
                    self.nodes[index + "." + key if index != '' else key] = MessageListNode.from_list(value)
                elif isinstance(value, dict):
                    index_messages(value, index + "." + key if index != '' else key)
                elif isinstance(value, str):
                    self.nodes[index + "." + key if index != '' else key] = MessageListNode.from_str(value)

        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config_dict = yaml.load(f, Loader=yaml.FullLoader)
                LangManager.__index_strings(config_dict['global_placeholders'], self.placeholders)
                index_messages(config_dict['messages'])

    def get(self, index: str):
        node = self.nodes.get(index)
        return node if node else LangManager.empty
