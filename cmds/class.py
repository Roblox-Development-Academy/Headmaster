import asyncio
from typing import Tuple, Optional, Dict
import re
from datetime import datetime, timezone, timedelta

import conditions
from bot import *
from prompt import prompt, Stage
from language import LangManager
import common
import errors

scheduled_classes: Dict[Tuple[int, str], Tuple[asyncio.Task, discord.Message]] = {}


async def on_ready():
    pass


async def schedule_class(teacher: discord.User, name: str, message: discord.Message, date: datetime,
                         channel_id: Optional[int], voice_channel_id: Optional[int],
                         guild_id: Optional[str]):
    await discord.utils.sleep_until(date)


def get_class_names(user_id: int) -> Tuple[Tuple[str]]:
    return database.query(
        """
        SELECT name
        FROM classes
        WHERE teacher = %s
        """,
        (user_id,)
    ).fetchall()


@prompt
async def __create(stage: Stage, name: str = None, interest_check: bool = False):
    ctx = stage.ctx
    results = stage.results
    dm = ctx.author.dm_channel or await ctx.author.create_dm()
    if stage.num == 0:
        if not ctx.guild:
            await lang.get('to_dms').send(ctx)
        if interest_check:
            results['title'] = "Interest Check"
        else:
            results['title'] = "Create Class"
        results['interest_check'] = interest_check
        results['name'] = name
        results['header'] = ''
        if not results['name']:
            await stage.zap(1)
        results['classes'] = [name[0] for name in get_class_names(ctx.author.id)]
        if results['name'] in results['classes']:
            results['header'] = lang.get('class.create.2').nodes[0].options.get('name_taken')
        else:
            results['header'] = lang.get('class.create.2').nodes[0].options.get('name_is')
        await stage.zap(2)
        in_prompt.pop(ctx.author.id, None)
    elif stage.num == 1:
        header = ''
        while True:
            results['name'] = (await common.prompt(dm, ctx.author, lang.get('class.create.1'),
                                                   header=header, title=results['title'])).content
            if not (1 < len(results['name']) < 32) or not re.search(r"^[\w ]+$", results['name']):
                header = lang.get('class.create.1').nodes[0].options.get('invalid_name', '')
            else:
                break
    elif stage.num == 2:
        description = await common.prompt(dm, ctx.author, lang.get('class.create.2'), timeout=900, back=stage.zap(1),
                                          time_display="15 minutes", header=results['header'], name=results['name'],
                                          title=results['title'])
        results['description'] = description
        await stage.zap(3)
    elif stage.num == 3:
        header = ''
        while True:
            try:
                prerequisites = await common.prompt(dm, ctx.author, lang.get('class.create.3'), timeout=900,
                                                    back=stage.zap(2), can_skip=True, time_display="15 minutes",
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
        results['prerequisites'] = prerequisites
        await stage.next()
    elif stage.num == 4:
        header = lang.get('class.create.4').nodes[0].options.get('prerequisites_is')
        try:
            msg = await common.prompt(dm, ctx.author, lang.get('class.create.4'), back=stage.back(), can_skip=True,
                                      header=header, prerequisites=results['prerequisites'].jump_url)
            if msg.attachments:
                results['image'] = msg.attachments[0].url
            else:
                results['image'] = msg.content
        except errors.PromptSkipped:
            pass
        if results['interest_check']:
            await stage.zap(8)
            return
        await stage.next()
    elif stage.num == 5:
        node = lang.get('class.create.5')
        img = results.get('image')
        if img:
            header = node.nodes[0].options.get('image_is')
        else:
            header = node.nodes[0].options.get('no_image')
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
            else:
                break
        await stage.next()
    elif stage.num == 6:
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
    elif stage.num == 7:
        response, _ = await common.prompt_reaction(lang.get('class.create.7'), ctx.author, dm,
                                                   allowed_emojis=('1\u20e3', '2\u20e3', '3\u20e3', "↩"))
        emoji = response.emoji
        if emoji == '1\u20e3':  # Server classroom
            results['classroom'] = lang.get('class.create.8').nodes[0].options.get('server', '')
        elif emoji == '2\u20e3':  # Text channel
            results['classroom'] = lang.get('class.create.8').nodes[0].options.get('text', '')
            results['channel'] = 1
        elif emoji == '3\u20e3':  # Text channel + voice channel
            results['classroom'] = lang.get('class.create.8').nodes[0].options.get('text_and_voice', '')
            results['channel'] = 1
            results['voice_channel'] = 1
        else:
            await stage.back()
            return
        await stage.next()
    elif stage.num == 8:
        confirm_emoji = lang.global_placeholders.get('emoji.confirm')
        return_emoji = lang.global_placeholders.get('emoji.return')
        node = lang.get('class.create.8')
        node.nodes[0].embed.timestamp = results.get('date', discord.Embed.Empty)
        response, _ = await common.prompt_reaction(node, ctx.author, dm, allowed_emojis=[confirm_emoji, return_emoji],
                                                   classroom=results.get('classroom', '*N/A; Interest Check*'),
                                                   description=results['description'].content,
                                                   prerequisites=results['prerequisites'].content)
        emoji = response.emoji
        if emoji == confirm_emoji:
            if results['interest_check']:
                in_prompt.pop(ctx.author.id)
                node = lang.get('class.interest_check')
                msgs = await node.send(class_channel, name=results['name'], description=results['description'].content,
                                       prerequisites=results['prerequisites'].content, image=results.get('image'),
                                       teacher=rda.get_member(ctx.author.id).nick, avatar=ctx.author.avatar_url)
                await lang.get('class.create.interest_check_completed').send(ctx.author, url=msgs[0].jump_url)
                return
            await stage.zap(100) if results.get('channel') else await stage.next()
        else:
            await stage.back()
    elif stage.num == 9:
        def check(g: discord.Guild):
            return g.owner_id == ctx.author.id

        guild: discord.Guild = await common.prompt_wait(dm, ctx.author, await lang.get('class.create.9'),
                                                        client.wait_for('guild_join', check), back=stage.back())
        results['guild'] = guild.id
        await stage.zap(100)
    elif stage.num == 100:
        in_prompt.pop(ctx.author.id)
        class_node = lang.get('class.class_info').replace(name=results['name'],
                                                          description=results['description'].content,
                                                          prerequisites=results['prerequisites'].content,
                                                          image=results.get('image'),
                                                          teacher=rda.get_member(ctx.author.id).nick,
                                                          avatar=ctx.author.avatar_url)
        class_node.nodes[0].args['embed'].timestamp = results['date']
        if results['max_students']:
            class_node.nodes[0].args['embed'].add_field(name="Maximum Students", inline=False,
                                                        value=class_node.nodes[0].options.get('max_students')
                                                        )
        class_msgs = await class_node.send(class_channel, mutilate=True, max_students=results['max_students'])
        node = lang.get('class.create.completed')
        node.nodes[0].args['embed'].timestamp = results['date']
        await node.send(ctx.author, url=class_msgs[0].jump_url)
        task = asyncio.create_task(schedule_class(ctx.author, results['name'], class_msgs[0], results['date'],
                                                  results.get('channel'), results.get('voice_channel'),
                                                  results.get('guild')))
        scheduled_classes[(ctx.author.id, results['name'])] = (task, class_msgs[0])
        try:
            await task
        except asyncio.CancelledError:
            pass


@commands.command(name="class", aliases=['classroom', 'classes', 'classrooms'], restisraw=True)
@conditions.in_rda()
async def class_(ctx, sub: str = None, name: str = ''):
    header = ''
    color = '%color.info%'
    node = lang.get('class.main')
    if sub:
        sub = sub.lower()
        if sub in ('schedule', 'create', 'start', 'make', 'begin', 'initiate'):
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
    node.nodes[0].args['embed'].color = discord.Color(int(LangManager.replace(color), 16))
    await node.send(ctx, name=name, classes=your_classes, header=header,
                    teacher_role=rda.get_role(673608309198028811).mention)


def setup(bot: commands.Bot):
    bot.add_command(class_)
