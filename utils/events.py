import asyncio
from typing import List, Callable, Dict

from discord.utils import maybe_coroutine


class Event:
    def __init__(self):
        self._handlers: List[Callable] = []
        self.signals: Dict[asyncio.Future, Callable] = {}

    def __call__(self, func: Callable):
        self._handlers.append(func)
        return func

    @staticmethod
    def __default_check():
        return True

    async def wait(self, check: Callable = __default_check, timeout: float = None, future: asyncio.Future = None):
        future = future or asyncio.get_event_loop().create_future()
        self.signals[future] = check
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.signals.pop(future)
            raise

    async def fire(self, *args, **kwargs):
        for handler in self._handlers:
            await maybe_coroutine(handler, *args, **kwargs)
        fired_signals = []
        for future, check in self.signals.items():
            if await maybe_coroutine(check, *args, **kwargs):
                future.set_result((*args, *kwargs.values()))
                fired_signals.append(future)
        for signal in fired_signals:
            self.signals.pop(signal)
