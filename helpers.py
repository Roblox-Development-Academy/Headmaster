import asyncio
from datetime import datetime
from dateutil.parser import parse
import pytz

from bot import *
import errors

message = {
    'cancel_prompt': "\n\nRespond with `cancel` to cancel the setup.",
    'respond_prompt:': "Please respond within 5 minutes"
}

"""
_tz_string = '''-12 Y
-11 X NUT SST
-10 W CKT HAST HST TAHT TKT
-9 V AKST GAMT GIT HADT HNY
-8 U AKDT CIST HAY HNP PST PT
-7 T HAP HNR MST PDT
-6 S CST EAST GALT HAR HNC MDT
-5 R CDT COT EASST ECT EST ET HAC HNE PET
-4 Q AST BOT CLT COST EDT FKT GYT HAE HNA PYT
-3 P ADT ART BRT CLST FKST GFT HAA PMST PYST SRT UYT WGT
-2 O BRST FNT PMDT UYST WGST
-1 N AZOT CVT EGT
0 Z EGST GMT UTC WET WT
1 A CET DFT WAT WEDT WEST
2 B CAT CEDT CEST EET SAST WAST
3 C EAT EEDT EEST IDT MSK
4 D AMT AZT GET GST KUYT MSD MUT RET SAMT SCT
5 E AMST AQTT AZST HMT MAWT MVT PKT TFT TJT TMT UZT YEKT
6 F ALMT BIOT BTT IOT KGT NOVT OMST YEKST
7 G CXT DAVT HOVT ICT KRAT NOVST OMSST THA WIB
8 H ACT AWST BDT BNT CAST HKT IRKT KRAST MYT PHT SGT ULAT WITA WST
9 I AWDT IRKST JST KST PWT TLT WDT WIT YAKT
10 K AEST ChST PGT VLAT YAKST YAPT
11 L AEDT LHDT MAGT NCT PONT SBT VLAST VUT
12 M ANAST ANAT FJT GILT MAGST MHT NZST PETST PETT TVT WFT
13 FJST NZDT
11.5 NFT
10.5 ACDT LHST
9.5 ACST
6.5 CCT MMT
5.75 NPT
5.5 SLT
4.5 AFT IRDT
3.5 IRST
-2.5 HAT NDT
-3.5 HNT NST NT
-4.5 HLV VET
-9.5 MART MIT'''

tz_data = {}
for tz_descr in (tz_spec.split() for tz_spec in _tz_string.split('\n')):
    tz_offset = int(float(tz_descr[0]) * 3600)
    for tz_code in tz_descr[1:]:
        tz_data[tz_code] = tz_offset
"""

tz_data = dict([(pytz.timezone(x).localize(datetime.now()).tzname(), pytz.timezone(x)) for x in pytz.all_timezones])


def convert_datetime(date: str) -> datetime:
    # TODO - Something wrong here! EDT and EST are different and they leave so much room for error because EDT is
    #  with daylight savings
    return parse(date.upper(), dayfirst=False, tzinfos=tz_data, fuzzy=False)


def usage_embed(usage, description, example=None):
    """Returns an embed detailing the usage of a command

    :param usage: Command usage in the format "command <arg> <arg> [<optional arg>]"
    :param description: The description of the command and parameters
    :param example: Example usage of the command
    """

    cmd = usage[:usage.index(" ")]

    embed = discord.Embed(title='Command Usage - ' + cmd, colour=EMBED_COLORS['info'],
                          description="**" + cmd + "**" + usage[usage.index(" "):])

    embed.add_field(name='Description', value=description)

    if example:
        embed.add_field(name='Example', value=f"`{example}`")

    return embed


async def prompt(channel: discord.TextChannel, user: discord.User, *args, prompt_msg: discord.Message = None,
                 timeout=300, **kwargs) -> discord.Message:
    """
    Prompts the specified user for a text response

    :param user: The specific user to prompt
    :param channel: The channel to send the prompt in
    :param prompt_msg: The message object to edit if error
    :param timeout: How many seconds before timeout
    :return: The user's response
    """
    # TODO - Add the user to a dictionary whose commands are not seen in the channel due to being in the prompt
    if not prompt_msg:
        prompt_msg = await channel.send(*args, **kwargs)

    def check(m):
        return m.author == user and m.channel == channel

    msg = None
    try:
        msg = await client.wait_for("message", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        raise errors.PromptTimeout("The prompt has timed out", prompt_msg)

    if msg.content.lower() == "cancel":
        raise errors.PromptCancelled("The prompt was cancelled", prompt_msg)

    return msg


def retrieve_assignments(user_id) -> tuple:
    """
    Retrieves all assignments assigned by the specified user

    :param userId: The id of the specified user
    :return: A tuple of tuples with assignment names
    """