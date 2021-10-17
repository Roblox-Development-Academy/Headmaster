import asyncio
from typing import Tuple, Optional, Dict
import re
from datetime import datetime, timezone, timedelta

import nextcord
from nextcord.ext import tasks

import conditions
from bot import *
from utils.prompt import prompt, Stage
from utils.language import LangManager, MessageNode
from utils import common
import errors
from nextcord.utils import escape_markdown

scheduled_classes: Dict[Tuple[int, str], Tuple[asyncio.Task, nextcord.Message]] = {}
class_index: int = 0


async def run():
    global class_index
    for __channel in class_category.text_channels:
        __match = re.search(r'classroom-(\d+)', __channel.name)
        if __match:
            class_index = max(int(__match.group(1)), class_index)
    classes = database.query(
        """
        SELECT teacher, name, message, starting_at, voice_channel, guild
        FROM classes
        """
    ).fetchall()
    for classroom in classes:
        task = asyncio.create_task(schedule_class(client.get_user(classroom[0]), classroom[1], classroom[2],
                                                  classroom[3], classroom[4], classroom[5]))
        scheduled_classes[(classroom[0], classroom[1])] = (task, await class_channel.fetch_message(classroom[2]))
        try:
            await task
        except asyncio.CancelledError:
            pass

    @tasks.loop(minutes=10.0)
    async def check_inactive_channel_classes():
        for channel in class_category.text_channels:
            match = re.search(r'classroom-(\d+)', channel.name)
            if not match:
                continue
            now = datetime.utcnow()
            last_messages = (await channel.history(limit=1).flatten())
            if (not last_messages and now - channel.created_at > timedelta(minutes=30)) or \
                    (last_messages and now - last_messages[0].created_at > timedelta(minutes=30)):
                await channel.delete()
                voice_channel: nextcord.VoiceChannel = nextcord.utils.get(class_category.voice_channels,
                                                                        name=channel.name)
                if voice_channel:
                    await voice_channel.delete()

    check_inactive_channel_classes.start()


asyncio.get_event_loop().create_task(run())


async def schedule_class(teacher: nextcord.User, name: str, message_id: int, date: datetime,
                         use_voice_channel: Optional[bool] = False, guild_id: Optional[str] = 0):
    await nextcord.utils.sleep_until(date)
    await asyncio.sleep(1)
    message = await class_channel.fetch_message(message_id)
    node = lang.get('class.class_starting').replace(teacher=teacher.mention, name=name, class_info=message.jump_url)
    reaction = nextcord.utils.find(lambda r: str(r.emoji) == lang.global_placeholders.get('emoji.enroll'),
                                  message.reactions)
    students = [u for u in (await reaction.users().flatten()) if u != client.user and u != teacher]
    teacher_invite = ''
    if guild_id:
        guild: nextcord.Guild = client.get_guild(guild_id)
        invite = None
        for channel in guild.text_channels:
            if channel.name == "class":
                invite = LangManager.replace(node.nodes[0].options.get('invite'),
                                             invite=(await channel.create_invite()))
                teacher_invite = invite
                break
        if not invite:
            if not guild.channels:
                invite = node.nodes[0].options.get('no_invite')
                teacher_invite = lang.get('class.your_class_starting').nodes[0].options.get('no_invite')
            else:
                try:
                    invite = LangManager.replace(node.nodes[0].options.get('invite'),
                                                 invite=(await guild.text_channels[0].create_invite()).url)
                except IndexError:
                    invite = LangManager.replace(node.nodes[0].options.get('invite'),
                                                 invite=(await guild.channels[0].create_invite()).url)
        node.replace(mutate=True, invite=invite)
    else:
        global class_index
        class_index += 1
        student_text_perms = nextcord.PermissionOverwrite(read_messages=True)
        overwrites_text = {
            rda.default_role: nextcord.PermissionOverwrite(read_messages=False),
            teacher: nextcord.PermissionOverwrite(read_messages=True, mention_everyone=True, manage_channels=True,
                                                 manage_messages=True, manage_permissions=True),
            **{student: student_text_perms for student in students}
        }
        channel = await class_category.create_text_channel(f"classroom-{str(class_index)}", overwrites=overwrites_text)
        if use_voice_channel:
            student_voice_perms = nextcord.PermissionOverwrite(view_channel=True)
            overwrites_voice = {
                rda.default_role: nextcord.PermissionOverwrite(view_channel=False),
                teacher: nextcord.PermissionOverwrite(connect=True, mute_members=True, deafen_members=True,
                                                     move_members=True, manage_channels=True, view_channel=True,
                                                     manage_permissions=True, priority_speaker=True),
                **{student: student_voice_perms for student in students}
            }
            await class_category.create_voice_channel(f"classroom-{str(class_index)}", overwrites=overwrites_voice)
        url = await channel.create_invite()
        invite = LangManager.replace(node.nodes[0].options.get('invite'), invite=url)
        teacher_invite = invite
        node.replace(mutate=True, invite=invite)
    for student in students:
        await node.send(student)
    await lang.get('class.your_class_starting').send(teacher, invite=teacher_invite, name=name,
                                                     class_info=message.jump_url, num_students=len(students))
    info_node = await MessageNode.from_message(message)
    info_node.args['embed'].add_field(name="Class has started", inline=False, value=invite)
    await info_node.edit(message)
    database.update(
        """
        DELETE FROM classes
        WHERE teacher = %s AND name = %s
        """,
        (teacher.id, name)
    )


def get_class_names(user_id: int) -> Tuple[Tuple[str]]:
    return database.query(
        """
        SELECT name
        FROM classes
        WHERE teacher = %s
        """,
        (user_id,)
    ).fetchall()


def validate_name(name: str):
    return (1 < len(name) <= 100) and re.search(r"^[\w '#%&!$)(+,./:-]+$", name)


@prompt()
async def __create(stage: Stage, name: str = None, interest_check: bool = False):
    ctx = stage.ctx
    results = stage.results
    dm = ctx.author.dm_channel or await ctx.author.create_dm()
    if stage.num == 0:
        if teacher_role not in rda.get_member(ctx.author.id).roles:
            await lang.get('error.teacher_only').send(ctx)
            return
        if ctx.guild:
            await lang.get('to_dms').send(ctx)
        if interest_check:
            results['title'] = "Interest Check"
        else:
            results['title'] = "Create Class"
        results['interest_check'] = interest_check
        results['name'] = name
        results['classes'] = [name[0] for name in get_class_names(ctx.author.id)]
        if not results['name']:
            await stage.zap(0.5)
            await stage.zap(1)
        elif not validate_name(results['name']):
            await stage.zap(1)
            await stage.zap(0.5)
        else:  # A proper name was provided on command execution
            await stage.zap(0.5)
        await stage.zap(2)
    elif stage.num == 0.5:  # Class tag
        if results['interest_check']:
            stage.history.pop(-1)
            results['tag'] = ''
            return
        header = ''
        if results['name']:
            header = lang.get('class.create.1').nodes[0].options.get(
                'next_header.' + ('name_is' if results['name'] not in results['classes'] else 'name_taken'), '')
        node = lang.get('class.create.0,5').replace(title=results['title'], header=header, name=results.get('name', ''))
        if results.get('name'):
            node.nodes[0].options['reactions'].append("↩")
        response, _ = await common.prompt_reaction(node, ctx.author, dm,
                                                   allowed_emojis=node.nodes[0].options['reactions'])
        emoji = response.emoji
        if emoji == '1\u20e3':
            results['tag'] = "Class"
        elif emoji == '2\u20e3':
            results['tag'] = "WMW"
        elif emoji == '3\u20e3':
            results['tag'] = "AMA"
        elif emoji == '4\u20e3':
            results['tag'] = "WMW/AMA"
        else:
            results[('', 1)] = {
                'next_header': ''
            }
            await stage.zap(1, progress_history=False)
            await stage.zap(0.5, progress_history=False)
            return
        results[stage.path] = {
            'next_header': lang.get('class.create.0,5').nodes[0].options.get('next_header')
        }
    elif stage.num == 1:  # Name
        node = lang.get('class.create.1')
        if results.get('name') and not validate_name(results['name']):
            header = node.nodes[0].options.get('invalid_name', '')
        elif results['interest_check']:
            header = ''
        else:
            header = results[stage.history[-2]]['next_header']
        while True:
            results['name'] = (await common.prompt(dm, ctx.author, node, header=header,
                                                   title=results['title'], tag=results.get('tag', ''))).content
            if not validate_name(results['name']):
                header = lang.get('class.create.1').nodes[0].options.get('invalid_name', '')
            else:
                break
        results[stage.path] = {
            'next_header': node.nodes[0].options.get(
                'next_header.' + ('name_is' if results['name'] not in results['classes'] else 'name_taken'), '')
        }
    elif stage.num == 2:  # Description
        node = lang.get('class.create.2')
        if results['interest_check']:  # In case the name was provided in command execution
            header = lang.get('class.create.1').nodes[0].options.get(
                'next_header.' + ('name_is' if results['name'] not in results['classes'] else 'name_taken'), '')
        else:
            header = results[stage.history[-2]]['next_header']

        async def interest_check_back():
            await stage.zap(1, progress_history=False)
            await stage.zap(2, progress_history=False)
        description = await common.prompt(dm, ctx.author, node, timeout=900, back=stage.back(return_to_stage=True)
                                          if not results['interest_check'] else interest_check_back(),
                                          time_display="15 minutes", header=header, name=results['name'],
                                          tag=results['tag'], title=results['title'])
        results['description'] = description
        await stage.next()
    elif stage.num == 3:  # Prerequisites
        header = ''
        while True:
            try:
                prerequisites = await common.prompt(dm, ctx.author, lang.get('class.create.3'), timeout=900,
                                                    back=stage.back(), can_skip=True, time_display="15 minutes",
                                                    description=results['description'].jump_url, header=header,
                                                    title=results['title'])
            except errors.PromptSkipped:
                results['prerequisites'] = None
                await stage.next()
                return
            if len(prerequisites.content) > 1024:
                header = lang.get('class.create.3').nodes[0].options.get('too_long', '')
            else:
                break
        results['prerequisites'] = prerequisites.content
        results['prerequisites_url'] = prerequisites.jump_url
        await stage.next()
    elif stage.num == 4:  # Optional image for class info
        node = lang.get('class.create.4')
        if results.get("invalid_image"):
            header = node.nodes[0].options.get('invalid_image_url')
        elif results['prerequisites']:
            header = LangManager.replace(node.nodes[0].options.get('prerequisites_is'),
                                         prerequisites=results['prerequisites_url'])
        else:
            header = node.nodes[0].options.get('no_prerequisites')

        async def back():
            results['invalid_image'] = None
            await stage.back()

        try:
            img_msg = await common.prompt(dm, ctx.author, lang.get('class.create.4'), back=back(), can_skip=True,
                                          header=header)
            if img_msg.attachments:
                results['image'] = img_msg.attachments[0].url
            else:
                results['image'] = escape_markdown(img_msg.content.rstrip())
        except errors.PromptSkipped:
            results['image'] = None  # In case they go back to remove the image
            pass
        if results['interest_check']:
            await stage.zap(8)
            return
        await stage.next()
    elif stage.num == 5:  # Maximum students
        results['invalid_image'] = None
        img = results.get('image')
        node = lang.get('class.create.5').replace(image=img)
        header = node.nodes[0].options.get('image_is' if img else 'no_image')
        if not img:
            node.nodes[0].args['embed'].set_thumbnail(url=nextcord.Embed.Empty)
        while True:
            try:
                response = await common.prompt(dm, ctx.author, node, back=stage.back(), can_skip=True, header=header,
                                               image=img)
                results['max_students'] = min(int(response.content), 200)
                assert 1 <= results['max_students']
            except errors.PromptSkipped:
                results['max_students'] = False
                break
            except (ValueError, AssertionError):
                header = node.nodes[0].options.get('invalid_int')
            except nextcord.HTTPException:  # invalid image url
                results['invalid_image'] = True
                stage.history.pop(-1)  # Remove this stage 5
                stage.history.pop(-1)  # Remove the previous stage 4 with the failed image
                await stage.zap(stage.num - 1)
                return
            else:
                break
        await stage.next()
    elif stage.num == 6:  # Date
        node = lang.get('class.create.6')
        header = node.nodes[0].options.get('max_students_is') if results['max_students'] else \
            node.nodes[0].options.get('no_max_students')
        while True:
            response = await common.prompt_date(dm, ctx.author, node, back=stage.back(), header=header,
                                                max_students=results['max_students'])
            if response is None:
                header = node.nodes[0].options.get('invalid_submission')
                continue
            max_date = datetime.now(timezone.utc) + timedelta(days=60)
            min_date = datetime.now(timezone.utc)
            if response > max_date:
                response = max_date
            elif response < min_date:
                response = min_date
            break
        results['date'] = response
        await stage.next()
    elif stage.num == 7:  # Classroom type
        response, _ = await common.prompt_reaction(lang.get('class.create.7'), ctx.author, dm,
                                                   allowed_emojis=('1\u20e3', '2\u20e3', '3\u20e3', "↩"))
        emoji = response.emoji
        if emoji == '1\u20e3':  # Server classroom
            results['classroom'] = lang.get('class.create.8').nodes[0].options.get('server', '')
        elif emoji == '2\u20e3':  # Text channel
            results['classroom'] = lang.get('class.create.8').nodes[0].options.get('text', '')
            results['channel'] = True
        elif emoji == '3\u20e3':  # Text channel + voice channel
            results['classroom'] = lang.get('class.create.8').nodes[0].options.get('text_and_voice', '')
            results['channel'] = True
            results['voice_channel'] = True
        else:
            await stage.back()
            return
        await stage.next()
    elif stage.num == 8:  # Confirm details/Create Interest Check
        confirm_emoji = lang.global_placeholders.get('emoji.confirm')
        return_emoji = lang.global_placeholders.get('emoji.return')
        node = lang.get('class.create.8').replace(classroom=results.get('classroom', '*N/A; Interest Check*'),
                                                  description=results['description'].content,
                                                  prerequisites=results['prerequisites'] or '*No prerequisites*')
        node.nodes[0].args['embed'].timestamp = results.get('date', nextcord.Embed.Empty)
        if results.get('image'):
            node.nodes[0].args['embed'].set_image(url=results['image'])
        try:
            response, _ = await common.prompt_reaction(node, ctx.author, dm,
                                                       allowed_emojis=[confirm_emoji, return_emoji])
        except nextcord.HTTPException:  # If it's an interest check, it goes directly to stage 8 with the image
            results['invalid_image'] = True
            stage.history.pop(-1)  # Remove this stage 8
            stage.history.pop(-1)  # Remove the previous stage 4
            await stage.zap(4)  # Go back to the image setting stage
            return
        emoji = response.emoji
        if emoji == confirm_emoji:
            if results['interest_check']:
                teacher = ctx.author
                node = lang.get('class.interest_check').replace(name=results['name'],
                                                                description=results['description'].content,
                                                                teacher=rda.get_member(ctx.author.id).nick or teacher,
                                                                avatar=ctx.author.avatar_url,
                                                                teacher_mention=ctx.author.mention)
                if results['prerequisites']:
                    node.nodes[0].args['embed'].insert_field_at(0, name="Prerequisites", inline=False,
                                                                value=results['prerequisites'])
                if results.get('image'):
                    node.nodes[0].args['embed'].set_image(url=results['image'])
                msgs = await node.send(class_channel)
                await lang.get('class.create.interest_check_completed').send(ctx.author, url=msgs[0].jump_url)
                return
            await stage.zap(100) if results.get('channel') else await stage.next()
        else:
            await stage.back()
    elif stage.num == 9:  # Create guild
        def check(g: nextcord.Guild):
            return g.owner_id == ctx.author.id

        invite = nextcord.utils.oauth_url(client.user.id, nextcord.Permissions(administrator=True))
        guild: nextcord.Guild = await common.prompt_wait(dm, ctx.author, lang.get('class.create.9'),
                                                        client.wait_for('guild_join', check=check), back=stage.back(),
                                                        invite=invite)
        results['guild'] = guild.id
        await stage.zap(100)
    elif stage.num == 100:
        int_date = int(results['date'].timestamp())
        class_node = lang.get('class.class_info').replace(name=results['name'],
                                                          tag=results['tag'],
                                                          description=results['description'].content,
                                                          teacher=rda.get_member(ctx.author.id).nick or ctx.author.name,
                                                          avatar=ctx.author.avatar_url,
                                                          teacher_mention=ctx.author.mention,
                                                          url_display_time=f"{WEB_URL}/display-time/?time={int_date}",
                                                          new_class_ping=roles['newclass_alert'].mention)
        options = class_node.nodes[0].options
        embed = class_node.nodes[0].args['embed']
        embed.timestamp = results['date']
        if 'AMA' in results['tag']:
            embed.insert_field_at(1, name=options['ama.name'], inline=False, value=options['ama.value'])
        if 'WMW' in results['tag']:
            embed.insert_field_at(1, name=options['wmw.name'], inline=False, value=options['wmw.value'])
        if results['max_students']:
            embed.insert_field_at(1, name="Maximum Students", inline=False,
                                  value=class_node.nodes[0].options.get('max_students'))
        if results['prerequisites']:
            embed.insert_field_at(2, name="Prerequisites", inline=False,
                                  value=results['prerequisites'])
        if results.get('image'):
            embed.set_image(url=results['image'])
        class_msgs = await class_node.send(class_channel, mutate=True, max_students=results['max_students'])
        node = lang.get('class.create.completed')
        node.nodes[0].args['embed'].timestamp = results['date']
        await node.send(ctx.author, url=class_msgs[0].jump_url)
        task = asyncio.create_task(schedule_class(ctx.author, results['name'], class_msgs[0].id, results['date'],
                                                  results.get('voice_channel'), results.get('guild')))
        scheduled_classes[(ctx.author.id, results['name'])] = (task, class_msgs[0])
        database.update(
            """
            DELETE FROM classes
            WHERE teacher = %s AND name = %s
            RETURNING message
            """,
            (ctx.author.id, results['name'])
        )
        if database.cursor.rowcount != 0:
            scheduled_classes.pop((ctx.author.id, results['name']), None)
            await (await class_channel.fetch_message(database.cursor.fetchone()[0])).delete()
        database.update(
            """
            INSERT INTO classes (teacher, name, message, guild, channel, voice_channel, starting_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (ctx.author.id, results['name'], class_msgs[0].id, results.get('guild'), results.get('channel'),
             results.get('voice_channel'), results.get('date'))
        )
        try:
            await task
        except asyncio.CancelledError:
            pass


@commands.command(name="class", aliases=['classroom', 'classes', 'classrooms'], restisraw=True)
@conditions.in_rda()
async def class_(ctx, sub: str = None, *, name: str = ''):
    header = ''
    color = '%color.info%'
    node = lang.get('class.main')
    if sub:
        sub = sub.lower()
        if sub in ('new', 'schedule', 'create', 'start', 'make', 'begin', 'initiate'):
            await __create(ctx, name)
            return
        elif sub == "check":
            await __create(ctx, name, interest_check=True)
            return
        elif sub in ('cancel', 'remove', 'delete') and name != '':
            database.update(
                """
                DELETE FROM classes
                WHERE teacher = %s
                AND name = %s
                """,
                (ctx.author.id, name)
            )
            if database.cursor.rowcount != 0:
                header = node.nodes[0].options.get('deleted_header')
                color = "%color.success%"
                key = (ctx.author.id, name)
                scheduled_classes[key][0].cancel()
                _, msg = scheduled_classes.pop(key)
                await msg.delete()
            else:
                header = node.nodes[0].options.get('not_found_header')
                color = "%color.error%"
        else:
            header = node.nodes[0].options.get('invalid_command_header')
            color = "%color.error%"
    your_classes = '\n'.join(name[0] for name in get_class_names(ctx.author.id)) or \
                   node.nodes[0].options.get('no_classes')
    node.nodes[0].args['embed'].color = nextcord.Color(int(LangManager.replace(color), 16))
    await node.send(ctx, name=name, classes=your_classes, header=header,
                    teacher_role=teacher_role.mention)


def setup(bot: commands.Bot):
    bot.add_command(class_)
