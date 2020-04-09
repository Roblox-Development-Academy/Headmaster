from bot import *


@client.command
async def apply(ctx):
    embed = discord.Embed(title="Apply for Teacher", colour=EMBED_COLORS['wizard'],
                          description='You need the Teacher role to create your own classes and teach students. '
                                      'You need only to satisfy the requirements and periodically teach '
                                      'lessons.\n\n Click the check mark below if you believe you satisfy these '
                                      'requirements and wish to apply to be a teacher at Roblox Developer Academy.')
    embed.add_field(name="Requirements", value="    - Mature\n"
                                               "    - Responsible\n"
                                               "    - Active\n"
                                               "    - Have advanced knowledge about the subject you're teaching")
    message = await ctx.send(embed=embed)
    confirm_emoji = EMOJIS['confirm']
    message.add_reaction(f"\{confirm_emoji}")

    _, reaction = client.wait_for("reaction_add")
    pass
