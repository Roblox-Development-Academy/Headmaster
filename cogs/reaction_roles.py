import asyncio
from typing import Dict, Tuple, List, Union, Optional
import itertools

import nextcord
import yaml

import conditions
import events
from bot import *
from utils.language import LangManager


class ReactionRoles(commands.Cog):
    messages: Dict[int, Tuple[str, int]] = {}
    profiles: Dict[str, List[Dict[str, nextcord.Role]]] = {}
    messages_config: dict

    def __init__(self):
        with open('config.yml', encoding='utf-8', mode='r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        msg_list: List[Dict[str, Union[str, int]]]
        for profile, msg_list in config['reaction_roles']['profiles'].items():
            ReactionRoles.profiles[profile] = \
                [{LangManager.replace(emoji): (roles[value] if isinstance(value, str) else rda.get_role(value))
                 for emoji, value in options.items()} for options in msg_list]
        messages = database.query(
            """
            SELECT message_id, channel_id, profile, profile_num
            FROM reaction_roles_messages
            """
        ).fetchall()

        async def populate_messages():
            messages_to_remove: List[str] = []
            for message_id, channel_id, profile_name, profile_num in messages:
                channel = client.get_channel(channel_id)
                if not channel:
                    continue
                try:
                    await channel.fetch_message(message_id)
                except nextcord.NotFound:
                    messages_to_remove.append(str(message_id))
                    continue
                ReactionRoles.messages[message_id] = (profile_name, profile_num)
            if messages_to_remove:
                database.update(
                    f"""
                    DELETE FROM reaction_roles_messages
                    WHERE message_id IN ({",".join(messages_to_remove)})
                    """
                )
        asyncio.create_task(populate_messages())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: nextcord.RawReactionActionEvent):
        await ReactionRoles.update_role(payload, add_role=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: nextcord.RawReactionActionEvent):
        await ReactionRoles.update_role(payload, add_role=False)
        
    @staticmethod
    async def update_role(payload: nextcord.RawReactionActionEvent, add_role: bool):
        try:
            profile, profile_num = ReactionRoles.messages[payload.message_id]
        except KeyError:
            return
        member: nextcord.Member = payload.member or not add_role and rda.get_member(payload.user_id)
        if not member:
            return
        profile_msgs = ReactionRoles.profiles[profile]
        options = profile_msgs[profile_num]
        role = options.get(str(payload.emoji))
        if role is None:
            return
        if add_role:
            if f"{profile}_header" in roles.keys():
                await member.add_roles(role, roles[f"{profile}_header"], reason="Reaction Role " + profile)
            else:
                await member.add_roles(role, reason="Reaction Role " + profile)
        else:
            await member.remove_roles(role, reason="Reaction Role " + profile)
            existing_roles = member.roles
            profile_roles = list(
                itertools.chain.from_iterable([profile_roles.values() for profile_roles in profile_msgs]))
            if f"{profile}_header" in roles.keys() and not any([role in existing_roles for role in profile_roles]):
                await member.remove_roles(roles[f"{profile}_header"], reason=f"Reaction Roles no {profile} roles left")
        try:
            await events.reaction_roles[profile].fire(member, add_role, role, profile_num, payload)
        except KeyError:
            pass
        try:
            await events.reaction_roles[f"{profile}.{profile_num}"].fire(member, add_role, role, payload)
        except KeyError:
            pass

    @staticmethod
    async def add_msg(template: str, msg: nextcord.Message, num_template: int = 0):
        database.update(
            """
            INSERT INTO reaction_roles_messages (message_id, channel_id, profile, profile_num)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (message_id) DO UPDATE SET profile = EXCLUDED.profile, profile_num = EXCLUDED.profile_num
            """,
            (msg.id, msg.channel.id, template, num_template)
        )
        ReactionRoles.messages[msg.id] = (template, num_template)
        for emoji in ReactionRoles.profiles[template][num_template].keys():
            if isinstance(emoji, int):
                emoji = client.get_emoji(emoji)
            await msg.add_reaction(emoji)

    @commands.command(aliases=['rr', 'reactionroles'])
    @conditions.manager_only()
    async def reaction_roles(self, _, sub: Optional[str], template: str, *, msg: nextcord.Message = None,
                             num_template: int = 0):
        if sub == "add":
            await ReactionRoles.add_msg(template, msg, num_template)
        # print("Sub:", sub, "Template:", template, "Msg:", str(msg))
