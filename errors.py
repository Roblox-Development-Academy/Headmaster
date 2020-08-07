from bot import *


class NotInRDA(commands.CheckFailure):
    pass


class CancelProcesses(commands.CommandError):
    pass


class PromptError(commands.CommandError):
    pass


class PromptKilled(PromptError):
    pass


class PromptCancelled(PromptKilled):
    pass


class PromptTimeout(PromptKilled):
    pass


class PromptSkipped(PromptError):
    pass


class PreviousPrompt(PromptError):
    pass
