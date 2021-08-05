from typing import Callable, Dict, Any, List, Tuple, Optional

import errors
from cogs import errorhandler
from bot import commands, in_prompt


class Stage:
    def __init__(self, func: Callable, handler: Callable, context: commands.Context, stage_num: int = 0):
        self.callback: Callable = func
        self.handler: Callable = handler
        self.ctx: commands.Context = context
        self.branch: str = ''
        self.num: float = stage_num
        self.history: List[Tuple[str, float]] = [(self.branch, self.num)]
        self.results: Dict[Any, Any] = {}

    @property
    def path(self) -> Tuple[str, float]:
        return self.branch, self.num

    @path.setter
    def path(self, value: Tuple[str, float]):
        self.branch, self.num = value

    async def zap(self, stage_num: float, *args, progress_history: bool = True, **kwargs):
        self.num = stage_num
        if progress_history:
            self.history.append((self.branch, self.num))
        try:
            return (await self.callback(self, *args, **kwargs)) or self.num
        except errors.PromptKilled:
            raise
        except errors.PromptError as e:
            await self.handler(self.ctx, e)

    async def to(self, branch: str, stage_num: float = 0, *args, **kwargs):
        self.branch = branch
        return await self.zap(stage_num, *args, **kwargs)

    async def back(self, *args, return_to_stage: bool = False, **kwargs):
        try:
            current_stage = self.history.pop(-1)
        except IndexError:
            channel = self.ctx.channel
            await self.handler(channel, errors.PreviousPrompt("Cannot go back to previous prompt", channel))
        else:
            await self.to(*self.history[-1], *args, progress_history=False, **kwargs)
            if return_to_stage:
                await self.to(*current_stage)

    async def next(self, increment: Optional[float] = 1, *args, **kwargs):
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
            finally:
                in_prompt.pop(ctx.author.id, None)
        return new_func
    return decorator
