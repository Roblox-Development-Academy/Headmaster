from typing import Callable, Dict, Any, List, Optional

import errors
from cogs import errorhandler
from bot import commands


class Stage:
    def __init__(self, func: Callable, handler: Callable, context: commands.Context, stage_num: int = 0):
        self.callback: Callable = func
        self.handler: Callable = handler
        self.ctx: commands.Context = context
        self.branch: str = ''
        self.num: int = stage_num
        self.history: List[int] = [stage_num]
        self.results: Dict[str, Any] = {}

    @property
    def path(self):
        return self.branch + str(self.num)

    @path.setter
    def path(self, value: str):
        i = value.rfind('.')
        self.branch = value[0:i]
        self.num = int(value[(i + 1):-1])

    async def zap(self, stage_num: int, *args, progress_history: bool = True, **kwargs):
        self.num = stage_num
        if progress_history:
            self.history.append(self.num)
        try:
            return (await self.callback(self, *args, **kwargs)) or self.num
        except errors.PromptKilled:
            raise
        except errors.PromptError as e:
            await self.handler(self.ctx, e)

    async def to(self, branch: str, stage_num: int = 0, *args, **kwargs):
        self.branch = branch
        return await self.zap(stage_num, *args, **kwargs)

    async def back(self, *args, **kwargs):
        self.history.pop(-1)
        await self.zap(self.history[-1], *args, progress_history=False, **kwargs)

    async def next(self, increment: Optional[int] = 1, *args, **kwargs):
        await self.zap(self.num + increment, *args, **kwargs)


def prompt(handler=errorhandler.process) -> Callable:
    def decorator(func) -> Callable:
        async def new_func(ctx: commands.Context, *args, stage_num: int = 0, **kwargs):
            try:
                return await func(Stage(func, handler, ctx, stage_num), *args, **kwargs)
            except errors.PromptKilled as e:
                raise e
            except errors.PromptError as e:
                await handler(ctx, e)
        return new_func
    return decorator
