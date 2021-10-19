from bot import *
import errors


def teacher_only():
    def predicate(ctx):
        # See if a member has a role on a certain, specific Discord server.
        # member = guild.get_member(user_id)
        # member.roles
        return True
    return commands.check(predicate)


def manager_only():
    def predicate(ctx):
        return ctx.author.id in (260608867292020737, 450375444450115585)
    return commands.check(predicate)

  
def in_rda():
    def predicate(ctx):
        if rda.get_member(ctx.author.id):
            return True
        raise errors.NotInRDA
    return commands.check(predicate)
