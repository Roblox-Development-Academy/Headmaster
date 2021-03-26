from typing import Dict, Tuple, List, Union, Optional
import itertools
import os

import yaml

import conditions
import events
from bot import *
from utils.language import LangManager


class ReactionRoles(commands.Cog):
    messages: Dict[int, Tuple[str, int]] = {}
    profiles: Dict[str, List[Dict[str, discord.Role]]] = {}
    messages_config: dict

    def __init__(self):
        with open('config.yml', encoding='utf-8', mode='r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        msg_list: List[Dict[str, Union[str, int]]]
        for profile, msg_list in config['reaction_roles']['profiles'].items():
            ReactionRoles.profiles[profile] = \
                [{LangManager.replace(emoji): (roles[value] if isinstance(value, str) else rda.get_role(value))
                 for emoji, value in options.items()} for options in msg_list]
        with open('reaction_roles_messages.yml', encoding='utf-8', mode='r') as f:
            ReactionRoles.messages_config = yaml.load(f, Loader=yaml.FullLoader)
        if os.environ['DEBUG'] == '1':
            pre_text = "test_"
        else:
            pre_text = ""
        for msg_id, value in ReactionRoles.messages_config[pre_text + 'messages'].items():
            profile = value
            profile_num: int = 0
            try:
                profile, profile_num = tuple(value.split('.'))
                profile_num = int(profile_num)
            except ValueError:
                pass
            ReactionRoles.messages[msg_id] = (profile, profile_num)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await ReactionRoles.update_role(payload, add_role=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await ReactionRoles.update_role(payload, add_role=False)
        
    @staticmethod
    async def update_role(payload: discord.RawReactionActionEvent, add_role: bool):
        try:
            profile, profile_num = ReactionRoles.messages[payload.message_id]
        except KeyError:
            return
        member: discord.Member = payload.member or not add_role and rda.get_member(payload.user_id)
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
                return
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
    async def add_msg(template: str, msg: discord.Message, num_template: int = 0):
        if os.environ['DEBUG'] == '1':
            pre_text = "test_"
        else:
            pre_text = ""
        ReactionRoles.messages_config[pre_text + 'messages'][msg.id] = f"{template}.{num_template}"
        with open('reaction_roles_messages.yml', encoding='utf-8', mode='w') as f:
            yaml.dump(ReactionRoles.messages_config, f, default_flow_style=False)  # Removes comments :/
        ReactionRoles.messages[msg.id] = (template, num_template)
        for emoji in ReactionRoles.profiles[template][num_template].keys():
            if isinstance(emoji, int):
                emoji = client.get_emoji(emoji)
            await msg.add_reaction(emoji)

    @commands.command(aliases=['rr', 'reactionroles'])
    @conditions.manager_only()
    async def reaction_roles(self, ctx, sub: Optional[str], template: str, *, msg: discord.Message = None,
                             num_template: int = 0):
        if sub == "add":
            await ReactionRoles.add_msg(template, msg, num_template)
        #  print("Sub:", sub, "Template:", template, "Msg:", str(msg))
