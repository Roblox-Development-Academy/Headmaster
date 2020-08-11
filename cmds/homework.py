from typing import Tuple, Optional, Dict, List
import datetime
import asyncio
import re

from discord.ext.commands import MemberConverter

import common
from bot import *
import errors
from language import LangManager, MessageNode
import database
from prompt import prompt, Stage

"""
Assignment has an assigner (tutor), name (identifier), description (message ID), a solution (message ID).
It also has whether to tell the solution right after submission (in DM) or the date/time to tell the solution after
submission (after which it would be deleted).
Assignments will be created in DM and the assigner need only to edit the message directly to change them.
Assignments will be submitted based on tutor and name.
On submission, the student only needs to use the assigner and the name and it will let the player know the description.
"""

min_interval = datetime.timedelta(seconds=0)
max_interval = datetime.timedelta(days=60)
scheduled_assignments: Dict[Tuple[int, str], Tuple[asyncio.Task]] = {}
scheduled_submissions: Dict[Tuple[int, str], List[asyncio.Task]] = {}


async def run():
    logger.info("Scheduling assignments and submissions.")
    assignments = database.query(
        """
        SELECT assigner, name, solution, date, delete_after_date
        FROM assignments
        WHERE date IS NOT NULL AND date > NOW()
        """
    ).fetchall()
    for assignment in assignments:
        await schedule_assignment(*assignment)
    submissions = database.query(
        """
        SELECT submitter, submissions.assigner, submissions.name, interval, submitted_at
        FROM submissions JOIN assignments
        ON submissions.assigner = assignments.assigner
        AND submissions.name = assignments.name
        AND interval IS NOT NULL
        """
    ).fetchall()
    for submission in submissions:
        await schedule_submission(client.get_user(submission[0]), client.get_user(submission[1]), submission[2],
                                  submission[3], submission[4])


asyncio.get_event_loop().create_task(run())


def get_assignment_names(user_id: int) -> Tuple[str]:
    """
    Retrieves all assignments assigned by the specified user

    :param user_id: The id of the specified user
    :return: A tuple of tuples with assignment names
    """
    return database.query(
        """
        SELECT name
        FROM assignments
        WHERE assigner = %s
        """,
        (user_id,)
    ).fetchall()


async def schedule_submission(submitter: discord.User, assigner: discord.User, name: str,
                              interval: datetime.timedelta = None, start: datetime.datetime = None, wait: bool = True):
    async def scheduling_process():
        if wait:
            await discord.utils.sleep_until(start + interval)
        solution_id = database.query(
            """
            SELECT solution
            FROM assignments
            WHERE assigner = %s AND name = %s
            """,
            (assigner.id, name)
        ).fetchone()
        solution_id = solution_id[0]
        if not solution_id:
            return
        try:
            solution = await assigner.fetch_message(solution_id)
        except discord.NotFound:
            pass
        else:
            await lang.get('assignment.submit.solution').send(submitter, assigner=assigner.mention, name=name)
            await (await MessageNode.from_message(solution)).send(submitter)
        if wait:
            database.update(
                """
                DELETE FROM submissions
                WHERE submitter = %s AND assigner = %s AND name = %s
                """,
                (submitter.id, assigner.id, name)
            )
    task = asyncio.create_task(scheduling_process())
    if scheduled_submissions.get((submitter.id, name)):
        scheduled_submissions[(submitter.id, name)].append(task)
    else:
        scheduled_submissions[(submitter.id, name)] = [task]
    try:
        await task
    except asyncio.CancelledError:
        pass


async def schedule_assignment(assigner_id: int, name: str, solution: int, date: datetime.datetime, delete_after: bool):
    async def scheduling_task():
        if not solution:
            return
        await discord.utils.sleep_until(date)
        submissions = database.query(
            """
            SELECT submitter
            FROM submissions
            WHERE assigner = %s AND name = %s
            """,
            (assigner_id, name)
        ).fetchall()
        try:
            solution_msg = await client.get_user(assigner_id).fetch_message(solution)
        except discord.errors.NotFound:
            return
        node = await MessageNode.from_message(solution_msg)
        for submitter_tuple in submissions:
            submitter = client.get_user(submitter_tuple[0])
            await lang.get('assignment.solution').send(submitter, name=name,
                                                       assigner=client.get_user(assigner_id).mention)
            await node.send(submitter)
        if delete_after:
            database.update(
                """
                DELETE FROM assignments
                WHERE assigner = %s AND name = %s
                """,
                (assigner_id, name)
            )
        database.update(
            """
            DELETE FROM submissions
            WHERE assigner = %s AND name = %s
            """,
            (assigner_id, name)
        )
    task = asyncio.create_task(scheduling_task())
    scheduled_assignments[(assigner_id, name)] = (task,)
    try:
        await task
    except asyncio.CancelledError:
        pass


async def add_assignment(*columns):
    database.update(
        """
        INSERT INTO assignments (assigner, name, description, solution, delete_after_date, date, interval)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (assigner, name) DO UPDATE SET description = EXCLUDED.description, solution = EXCLUDED.solution,
        delete_after_date = EXCLUDED.delete_after_date, date = EXCLUDED.date, interval = EXCLUDED.interval
        """,
        columns
    )
    if columns[-2]:  # If schedule by date
        await schedule_assignment(columns[0], columns[1], columns[3], columns[-2], columns[-3])


def validate_name(name: str):
    return (1 < len(name) < 32) and re.search(r"^[\w :-]+$", name)


@prompt()
async def __create(stage: Stage, name: str = ''):
    ctx = stage.ctx
    results = stage.results
    dm = ctx.author.dm_channel or await ctx.author.create_dm()

    back = stage.back()

    if stage.num == 0:
        results['assignments'] = [x[0] for x in get_assignment_names(ctx.author.id)]
        results['name'] = name
        if len(results['assignments']) >= 10:
            await lang.get('assignment.error.too_many').send(ctx)
            return
        if ctx.channel != dm:
            await lang.get('to_dms').send(ctx)
        if not name or not validate_name(name):
            await stage.zap(1)
        else:
            stage.history.append(1)
            results['name'] = name
            await stage.zap(2)

        # After the wizard is completed
        while True:
            stage.history.append(stage.num)
            use_date = results.get('use_date')
            if use_date:
                time = "The solution will be sent to all submitters at the date and time below, which is in your " \
                       "local timezone."
                results['interval'] = None
            elif use_date is False:
                time = f"The solution will be sent {common.td_format(results['interval'])} after submitters submit " \
                       f"the assignment."
                results['date'] = None
            else:
                time = None
                results['date'] = None

            node = lang.get('assignment.create.confirm').replace(name=results['name'],
                                                                 description_url=results['description_url'],
                                                                 solution_url=results.get("solution_url"), time=time)
            if use_date:
                node.nodes[0].args['embed'].timestamp = results['date']
            elif use_date is None:
                node.nodes[0].args['embed'].remove_field(2)
                node.nodes[0].args['embed'].remove_field(2)
            confirm_emoji = lang.global_placeholders.get('emoji.confirm')
            return_emoji = lang.global_placeholders.get('emoji.return')
            response, _ = await common.prompt_reaction(node, ctx.author, dm,
                                                       allowed_emojis=[confirm_emoji, return_emoji])
            if response.emoji == return_emoji:
                await back
                continue
            in_prompt.pop(ctx.author.id)
            await lang.get('assignment.create.completed').send(dm, name=results['name'], assigner=ctx.author.mention)
            await add_assignment(ctx.author.id, results['name'], results['description_id'], results.get('solution_id'),
                                 results.get('delete_after_date'), results.get('date'), results.get('interval'))
            return
    elif stage.num == 1:
        if results['name'] and not validate_name(results['name']):
            header = lang.get('assignment.create.1').nodes[0].options['invalid_name']
        else:
            header = ''
        while True:
            results['name'] = (await common.prompt(dm, ctx.author, lang.get('assignment.create.1'),
                                                   header=header)).content
            if not results['name']:
                header = "**The name must be longer than 0 characters!**\n\n"
            elif len(results['name']) > 32:
                header = "**The name is too long! It cannot be longer than 32 characters!**\n\n"
            else:
                break
        await stage.next()
    elif stage.num == 2:
        header = "__**The name of this assignment is `%name%`**__"
        if results['name'] in results['assignments']:
            header = "__**The name, `%name%`, is already taken. Completing the creation will replace the " \
                     "assignment. Respond with `back` to go to the previous stage.**__"
        description = await common.prompt(dm, ctx.author, lang.get('assignment.create.2'), timeout=900, back=back,
                                          name=results['name'], header=header, time_display="15 minutes")
        results['description_id'] = description.id
        results['description_url'] = description.jump_url
        await stage.next()
    elif stage.num == 3:
        results['solution_id'] = None
        try:
            solution = await common.prompt(dm, ctx.author, lang.get('assignment.create.3'), timeout=900, back=back,
                                           can_skip=True, time_display="15 minutes", url=results["description_url"])
            results['solution_id'] = solution.id
            results['solution_url'] = solution.jump_url
            await stage.next()
        except errors.PromptSkipped:
            return
    elif stage.num == 4:
        option, _ = await common.prompt_reaction(lang.get('assignment.create.4'), ctx.author, dm,
                                                 allowed_emojis=('1\u20e3', '2\u20e3', '3\u20e3', "↩"),
                                                 url=results['solution_url'])
        emoji = option.emoji
        if emoji == '1\u20e3':
            results['use_date'] = False
            await stage.zap(5)
        elif emoji == '2\u20e3':
            results['use_date'] = False
            await stage.zap(6)
        elif emoji == '3\u20e3':
            results['use_date'] = True
            await stage.zap(7)
        else:
            await back
    elif stage.num == 5:  # Send solution immediately after submission
        results['interval'] = datetime.timedelta(seconds=0)
    elif stage.num == 6:  # Send solution after an interval
        interval = None
        while True:
            response = (await common.prompt(dm, ctx.author, lang.get('assignment.create.6'), back=back)).content
            try:
                interval = common.parse_interval(response, minimum=min_interval, maximum=max_interval)
            except OverflowError:
                await lang.get('error.interval.range', range_display="2 months").send(dm)
                continue

            if interval is not None:
                break
            else:
                await lang.get('error.interval.parse').send(dm)
        results['interval'] = interval
    elif stage.num == 7:  # Send solution at a certain date
        header = ""
        while True:
            response = (await common.prompt_date(dm, ctx.author, lang.get('assignment.create.7'), back=back,
                                                 header=header))

            if response is None:
                header = "**Invalid submission. Please try again.**\n\n"
                continue

            max_date = datetime.datetime.now(datetime.timezone.utc) + max_interval
            min_date = datetime.datetime.now(datetime.timezone.utc)
            if response > max_date:
                response = max_date
            elif response < min_date:
                response = min_date
            break
        results['date'] = response
        await stage.next()
    elif stage.num == 8:
        response, _ = await common.prompt_reaction(lang.get('assignment.create.8'), ctx.author, dm,
                                                   allowed_emojis=['1\u20e3', '2\u20e3',
                                                                   lang.global_placeholders.get('emoji.return')])
        emoji = response.emoji
        if emoji == '1\u20e3':
            results['delete_after_date'] = True
        elif emoji == '2\u20e3':
            results['delete_after_date'] = False
        else:
            await back


@prompt()
async def __submit(stage: Stage, sub: str = None, name: str = None, assigner: discord.User = None):
    ctx = stage.ctx
    channel = (ctx.author.dm_channel or await ctx.author.create_dm()) \
        if (sub or stage.results['sub']) == "submit" else ctx.channel
    if stage.num == 0:
        if ctx.guild and sub == "submit":
            await lang.get('to_dms').send(ctx.channel)
        stage.results['sub'] = sub
        stage.results['assigner'], stage.results['name'] = assigner, name
        if stage.results['assigner'] is None:
            if stage.results['sub'] == 'submit':
                await stage.zap(1)
            else:
                stage.results['assigner'] = ctx.author
        stage.results['header'] = ''
        while True:
            stage.results['assignments'] = [name[0] for name in get_assignment_names(stage.results['assigner'].id)]
            if stage.results['name'] is None:
                await stage.zap(2)
            if stage.results['name'] not in stage.results['assignments']:
                stage.results['header'] = "**The specified assignment could not be found!**\n\n"
                stage.results['name'] = None
            else:
                stage.results['info'] = database.query(
                    """
                    SELECT description, date, interval
                    FROM assignments
                    WHERE assigner = %s AND name = %s
                    """,
                    (stage.results['assigner'].id, stage.results['name'])
                ).fetchone()
                if not stage.results['info']:
                    stage.results['header'] = "**This assignment no longer exists!**\n\n"
                else:
                    break
        await stage.zap(3)
    elif stage.num == 1:
        header = ''
        while True:
            response = (await common.prompt(channel, ctx.author, lang.get('assignment.submit.1'),
                                            header=header, sub=stage.results['sub'].capitalize())).content
            try:
                stage.results['assigner']: discord.User = await MemberConverter().convert(ctx, response)
            except commands.errors.BadArgument:
                header = '**User not found! Please try again.**\n\n'
            else:
                break
    elif stage.num == 2:
        assignments = '\n'.join(stage.results['assignments']) or \
                      '*This user has created no assignments*'
        stage.results['name'] = (await common.prompt(channel, ctx.author, lang.get('assignment.submit.2'),
                                                     back=stage.zap(1), header=stage.results['header'],
                                                     sub=stage.results['sub'].capitalize(), list=assignments)).content
    elif stage.num == 3:
        try:
            description = await stage.results['assigner'].fetch_message(stage.results['info'][0])
        except discord.NotFound:
            description = None
        list_node = lang.get('assignment.submit.3')
        if stage.results['sub'] == 'submit':
            color = "%color.wizard%"
            is_submitting = True
            instructions = lang.get('assignment.submit.3').nodes[0].options.get('submit_instructions', '')
            list_node.nodes[0].args['embed'].footer.text = ""
        else:
            color = "%color.info%"
            is_submitting = False
            instructions = ''
        list_node.nodes[0].args['embed'].color = discord.Color(int(LangManager.replace(color), 16))
        msgs = await list_node.send(channel, sub=stage.results['sub'].capitalize(), name=stage.results['name'],
                                    assigner=stage.results['assigner'].mention, instructions=instructions)
        if description:
            await (await MessageNode.from_message(description)).send(channel)
        if is_submitting:
            submission = await common.prompt(channel, ctx.author, msgs[0], timeout=900, back=stage.back())
            in_prompt.pop(ctx.author.id)
            await lang.get('assignment.submit.complete').send(ctx.author, assigner=stage.results['assigner'].mention)
            await lang.get('assignment.submit.submission').send(stage.results['assigner'], name=stage.results['name'],
                                                                submitter=ctx.author.mention)
            await (await MessageNode.from_message(submission)).send(stage.results['assigner'])
            if stage.results['info'][1] is not None and \
                    stage.results['info'][1] < datetime.datetime.now(datetime.timezone.utc):
                # If it's past time, don't save
                await schedule_submission(ctx.author, stage.results['assigner'], stage.results['name'], wait=False)
            else:
                database.update(
                    """
                    INSERT INTO submissions (submitter, assigner, name, submitted_at)
                    values (%s, %s, %s, %s)
                    ON CONFLICT (submitter, assigner, name) DO UPDATE SET submitted_at = EXCLUDED.submitted_at
                    """,
                    (ctx.author.id, stage.results['assigner'].id, stage.results['name'],
                     datetime.datetime.now(datetime.timezone.utc))
                )
                if stage.results['info'][2] is not None:  # If interval
                    await schedule_submission(ctx.author, stage.results['assigner'], stage.results['name'],
                                              stage.results['info'][2], datetime.datetime.now(datetime.timezone.utc))
        else:
            in_prompt.pop(ctx.author.id, None)


@commands.command(aliases=['hw', 'assignment', 'assignments'])
async def homework(ctx, sub=None, assigner: Optional[discord.User] = None, *, name: Optional[str]):
    header = ''
    title = 'Assignments'
    color = '%color.info%'
    if sub is not None:
        sub = sub.lower()
        if sub in ("assign", "create", "start", "initiate", "make"):
            await __create(ctx, name)
            return
        elif sub in ("remove", "delete", "unassign", "cancel") and name is not None:
            database.update(
                """
                DELETE FROM assignments
                WHERE assigner = %s
                AND name = %s
                """,
                (ctx.author.id, name)
            )
            if database.cursor.rowcount != 0:
                header = f"**`{name}` was successfully deleted!**\n\n"
                color = "%color.success%"
                task = scheduled_assignments.get((ctx.author.id, name))
                if task:
                    task[0].cancel()
                    scheduled_assignments.pop((ctx.author.id, name))
                else:
                    tasks = scheduled_submissions.get((ctx.author.id, name))
                    if tasks:
                        for task in tasks:
                            task.cancel()
                        scheduled_submissions.pop((ctx.author.id, name))
            else:
                header = f"**You have not assigned an assignment named `{name}`.\n\n"
                color = "%color.error%"
        elif sub in ('submit', 'view', 'show', 'read'):
            await __submit(ctx, sub, name, assigner)
            return
        else:
            title = "Assignments - Invalid Command"
            color = "%color.error%"
    list_node = lang.get('assignment.main')
    your_assignments = "\n".join(name[0] for name in get_assignment_names(ctx.author.id)) or \
                       list_node.nodes[0].options.get('no_assignments')
    list_node = list_node.replace(title=title, header=header, assignments=your_assignments)
    list_node.nodes[0].args['embed'].color = discord.Color(int(LangManager.replace(color), 16))
    await list_node.send(ctx)


def setup(bot: commands.Bot):
    bot.add_command(homework)
