from typing import Callable, Dict, Any, List

import errors
from cogs import errorhandler
from bot import commands


class Stage:
    def __init__(self, func: Callable, handler: Callable, context: commands.Context, stage_num: int = 0):
        self.callback: Callable = func
        self.handler: Callable = handler
        self.ctx: commands.Context = context
        self.num: int = stage_num
        self.history: List[int] = [stage_num]
        self.results: Dict[str, Any] = {}

    async def zap(self, stage_num: int, *args, progress_history: bool = True, **kwargs):
        self.num = stage_num
        if progress_history:
            self.history.append(self.num)
        try:
            return await self.callback(self, *args, **kwargs)
        except errors.PromptKilled as e:
            raise e
        except errors.PromptError as e:
            await self.handler(self.ctx, e)

    async def back(self, *args, **kwargs):
        last_stage = self.history[-2]
        self.history.pop(-1)
        await self.zap(last_stage, *args, progress_history=False, **kwargs)

    async def next(self, *args, **kwargs):
        await self.zap(self.num + 1, *args, **kwargs)


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
