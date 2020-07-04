from cogs import errorhandler


class Stage:
    def __init__(self, func, handler, context, stage_num=0):
        self.callback = func
        self.handler = handler
        self.ctx = context
        self.num = stage_num
        self.results = {}

    async def zap(self, stage_num, *args, **kwargs):
        self.num = stage_num
        try:
            return await self.callback(self, *args, **kwargs)
        except Exception as e:
            await self.handler(self.ctx, e)


def prompt(handler=errorhandler.recursively_process):
    def decorator(func):
        async def new_func(ctx, *args, stage_num: int = 0, **kwargs):
            try:
                return await func(Stage(func, handler, ctx, stage_num), *args, **kwargs)
            except Exception as e:
                await handler(ctx, e)
        return new_func
    return decorator
