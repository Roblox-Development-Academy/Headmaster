import hashlib

import events
import errors
from bot import *
from web.app import get_digest, StaffApplication
from utils.debounce import Debounce


secret_key = str(TOKEN).encode()


def get_applicant_id(user_id: int):  # For footer of public staff applications channel
    return hashlib.blake2b(str(user_id).encode('utf-8'), key=secret_key, digest_size=16).hexdigest()


async def embed_to_dict():
    """
    Converts from private application embed to a dictionary for the staff form on the website to allow applicants to
    edit their responses.
    """
    pass


@events.reaction_roles.staff_applicant
@Debounce(failed_value=None, params=["member"])
async def send_info(member, add_role, *_):
    if add_role:
        await lang.get('staff_application.info').send(member,
                                                      applications_channel=channels['staff_application'].mention)


@events.staff_application_submitted
async def post_staff_application(user_id: int, form: StaffApplication):
    pass


class StaffApplication(commands.Cog):
    @commands.command(aliases=['applystaff', 'staff', 'staffapply', 'staff_apply'])
    async def apply_staff(self, ctx: commands.Context):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        member = rda.get_member(ctx.author.id)
        if not member:
            raise errors.NotInRDA
        if roles['staff_applicant'] not in member.roles:
            await lang.get('staff_application.error.no_role')\
                .send(ctx, staff_applicant_role=(roles['staff_applicant'].mention
                                                 if ctx.guild == rda else "Staff Applicant"))
            return
        digest = get_digest(ctx.author.id)
        url = f"{WEB_URL}/staff-application/?digest={digest}&user-id={member.id}"
        await lang.get('staff_application.apply').send(member, url=url,
                                                       applications_channel=channels['staff_application'].mention)
