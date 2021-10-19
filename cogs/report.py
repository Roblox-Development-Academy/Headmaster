from datetime import timezone, datetime
from nextcord.ext import commands
from bot import lang, client, report_channel
from utils.language import MessageNode
from utils.common import to_unix
from nextcord import Embed
from nextcord.errors import HTTPException


class Report(commands.Cog):
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) == lang.global_placeholders.get("emoji.report"):
            message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)
            if message.author == client.user:
                await lang.get("error.report").send(message.channel)
                return
            # time_format = '%A, %B %d, %Y; %I:%M %p UTC'
            await lang.get("report.start").send(report_channel, reported=f"{message.author}",
                                                reported_id=str(message.author.id), reporter=f"{payload.member}",
                                                reporter_id=str(payload.member.id), guild_name=message.guild.name,
                                                guild_id=str(message.guild.id), channel_name=message.channel.name,
                                                channel_id=str(message.channel.id), jump_url=message.jump_url,
                                                message_id=str(message.id),
                                                message_sent_at=to_unix(message.created_at),
                                                report_time=to_unix(datetime.now(timezone.utc)))
            message_copy = await MessageNode.from_message(message)
            try:
                await message_copy.send(report_channel)
            except HTTPException:
                await report_channel.send(embed=Embed(description="The reported message has no content.",
                                                      colour=int(lang.global_placeholders.get("color.error"), 16)))
            await lang.get("report.end").send(report_channel)
            await lang.get("report.success").send(payload.member, reported_id=str(message.author.id),
                                                  reported_name=message.author.name)
