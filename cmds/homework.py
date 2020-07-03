import common
from bot import *
import errors
from cogs import errorhandler
from language import LangManager
import database

"""
Assignment has an assigner (tutor), name (identifier), description (message ID), a solution (message ID).
It also has whether to tell the solution right after submission (in DM) or the date/time to tell the solution after
submission (after which it would be deleted).
Assignments will be created in DM and the assigner need only to edit the message directly to change them.
Assignments will be submitted based on tutor and name.
On submission, the student only need to use the assigner and the name and it will let the player know the description.
"""


def get_assignment_names(user_id) -> tuple:
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


async def __create(ctx, name='', num_stage=0, results=None):
    dm = ctx.author.dm_channel or await ctx.author.create_dm()

    if results is None:
        results = {}

    async def back():
        try:
            await __create(ctx, num_stage=num_stage - 1, results=results)
        except Exception as e:
            await errorhandler.process_errors(ctx, e)

    if num_stage == 0:
        if ctx.channel != dm:
            await lang.get('assignment.create.start').send(ctx)
        if not name:
            await __create(ctx, num_stage=1, results=results)
        else:
            results['name'] = name
            await __create(ctx, num_stage=1 if len(name) > 32 else 2, results=results)

        in_prompt.pop(ctx.author.id)  # TODO - An error (such as 'back') will break the thread and this won't run;
        # maybe put this in a "last stage", instead
        # ~ a wizard prompt class would be great
    elif num_stage == 1:
        if len(results.get('name', '')) > 31:
            header = "**The name is too long! It cannot be longer than 31 characters!**\n\n"
        else:
            header = ''
        while True:
            results['name'] = (await common.prompt(dm, ctx.author, lang.get('assignment.create.1'),
                                                   header=header)).content
            if not results['name']:
                header = "**The name must be longer than 0 characters!**\n\n"
            elif len(results['name']) > 31:
                header = "**The name is too long! It cannot be longer than 31 characters!**\n\n"
            else:
                break
        await __create(ctx, num_stage=2, results=results)
    elif num_stage == 2:
        header = "__**The name of this assignment is `%name%`**__"
        if results['name'] in (x[0] for x in get_assignment_names(ctx.author.id)):
            header = "__**The name, `%name%`, is already taken. Completing the creation will replace the " \
                     "assignment. Respond with `back` to go to the previous stage.**__"
        description = await common.prompt(dm, ctx.author, lang.get('assignment.create.2'), timeout=900, back=back(),
                                          name=results['name'], header=header, time_display="15 minutes")
        results['description_id'] = description.id
        results['description_url'] = description.jump_url
        await __create(ctx, num_stage=3, results=results)
    elif num_stage == 3:
        results['solution_id'] = None
        try:
            solution = await common.prompt(dm, ctx.author, lang.get('assignment.create.3'), timeout=900, back=back(),
                                           can_skip=True, time_display="15 minutes", url=results["description_url"])
            results['solution_id'] = solution.id
            results['solution_url'] = solution.jump_url
            await __create(ctx, num_stage=4, results=results)
        except errors.PromptSkipped:
            return
    elif num_stage == 4:
        option, _ = await common.prompt_reaction(lang.get('assignment.create.4'), ctx.author, dm,
                                                 allowed_emojis=('1\u20e3', '2\u20e3', '3\u20e3'),
                                                 url=results['solution_url'])
        pass


async def __submit(ctx, assigner, name=None):
    pass


@commands.command(aliases=['name', 'hw', 'assignment', 'assignments'])
async def homework(ctx, sub=None, name=None, assigner: discord.Member = None):
    header = ''
    title = 'Assignments'
    color = '%color.info%'
    if sub is not None:
        if sub.lower() in ("assign", "create", "start", "initiate", "make"):
            await __create(ctx, name)
            return
        elif sub.lower() in ("remove", "delete", "unassign") and name is not None:
            database.update(
                """
                DELETE FROM assignments
                WHERE assigner = %s
                AND name = %s
                """,
                (ctx.author.id, name)
            )
            if database.cursor.rowcount != 0:
                header = f"**{name} was successfully deleted!\n\n"
                color = "%color.success%"
            else:
                header = f"**{name} does not exist!!\n\n"
                color = "%color.error%"
            # TODO - Also has to delete it from current scheduling process
        elif sub.lower() == "submit":
            await __submit(ctx, name, assigner)
            return
        else:
            title = "Assignments - Unrecognized Command"
            color = "%color.error%"
    list_node = lang.get('assignment.main')
    your_assignments = "\n".join(name[0] for name in get_assignment_names(ctx.author.id)) or \
                       list_node.nodes[0].options.get('no_assignments')
    list_node = list_node.replace(title=title, header=header, assignments=your_assignments,
                                  prefix=get_prefix(ctx.guild.id) if ctx.guild else
                                  lang.global_placeholders.get('default_prefix'))
    list_node.nodes[0].args['embed'].color = discord.Color(int(LangManager.replace(color), 16))
    await list_node.send(ctx)


def setup(bot: commands.Bot):
    bot.add_command(homework)
