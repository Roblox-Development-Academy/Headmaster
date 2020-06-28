from bot import *


def teacher_only():
    def predicate():
        # TODO Is there any way to see if a member has a role on a certain, specific Discord server?
        return True
    return commands.check(predicate)
