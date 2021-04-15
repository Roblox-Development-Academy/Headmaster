"""
For some reason, I decided to write this entire file on my phone ._.
"""
import asyncio
import functools
import inspect
from typing import Callable, Dict, Any, Iterable
from datetime import timedelta, datetime


class DebounceException(Exception):
    def __init__(self, *args: timedelta):
        self.time_left: timedelta = args[0]

    def __str__(self):
        return "DebounceException: " + str(self.time_left.total_seconds()) + " seconds left!"


class Debounce:
    def __init__(self, debounce: timedelta = timedelta(minutes=3), failed_value=..., params: Iterable[str] = tuple()):
        self.debounce: timedelta = debounce
        self.failed_value: Any = failed_value
        self.last_called: datetime = datetime.fromtimestamp(0)
        self.params: Dict[str, Dict[Any, datetime]] = {}
        # Btw, if you store the end times instead of the last called times, you can have param-specific debounces
        for arg in params:
            self.params[arg] = {}

    def __call__(self, func: Callable):
        sig = inspect.signature(func)

        @functools.wraps(func)
        def new_func(*args, **kwargs):
            for param, values in self.params.items():
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                value = bound_args.arguments[param]
                if value:
                    last_called = values.get(value)
                    if last_called is not None:
                        # Debounce failed
                        if self.failed_value is ...:
                            raise DebounceException(self.debounce - (datetime.utcnow() - last_called))
                        else:
                            return self.failed_value
                    else:
                        values[value] = datetime.utcnow()

                        async def reset_debounce():
                            await asyncio.sleep(self.debounce.total_seconds())
                            del values[value]

                        asyncio.create_task(reset_debounce())
            if not self.params:
                now = datetime.utcnow()
                if now - self.last_called < self.debounce:
                    if self.failed_value is ...:
                        raise DebounceException(self.debounce - (now - self.last_called))
                    else:
                        return self.failed_value
                else:
                    self.last_called = now
            return func(*args, **kwargs)

        new_func.debounce = self
        func.debounce = self
        return new_func


"""
@Debounce(timedelta(seconds=5), params=["name"])
async def foo(name):
    print("Hello", name)


async def run():
    await foo("JL")
    await foo("Coney")
    await asyncio.sleep(2)
    try:
        await foo("JL")
    except DebounceException as e:
        print(e)
    await asyncio.sleep(3.1)
    await foo("JL")


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
"""
