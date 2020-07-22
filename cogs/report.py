from datetime import timezone, datetime
from discord.ext import commands
from yaml import load, FullLoader
from bot import lang
from language import MessageNode
import discord


class Report(commands.Cog):
    def __init__(self, client):
        self.client = client
        with open("config.yml") as f:
            config = load(f, Loader=FullLoader)
            self.report_channel = config['channels']['report']

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if str(payload.emoji) == lang.global_placeholders.get("emoji.report"):
            report_channel = self.client.get_channel(self.report_channel)
            await message.remove_reaction(payload.emoji, payload.member)
            await lang.get("report.start").send(report_channel, reported=f"{message.author}", reported_id=str(message.author.id), reporter=f"{payload.member}", reporter_id=str(payload.member.id), guild_name=message.guild.name, guild_id=str(message.guild.id), channel_name=message.channel.name, channel_id=str(message.channel.id), jump_url=message.jump_url, message_id=str(message.id), message_sent_at=str(message.created_at), report_time=str(datetime.now(timezone.utc)))
            message_copy = await MessageNode.from_message(message)
            await message_copy.send(report_channel)
            await lang.get("report.end").send(report_channel)
            await lang.get("report.success").send(payload.member, reported_id=str(message.author.id), reported_name=message.author.name)
