from bot import *


class PromptCancelled(commands.CommandError):
    pass


class PromptTimeout(commands.CommandError):
    pass


class PromptSkipped(commands.CommandError):
    pass