import asyncio
import functools
import inspect
from typing import Callable, Dict, Any, Iterable, Tuple, Union
from datetime import timedelta, datetime


"""
Possible improvements:
- accept and implement *args and **kwargs in param check function to match original function
- debounce by return value option, not just parameters
"""


class DebounceException(Exception):
    def __init__(self, *args: timedelta):
        self.time_left: timedelta = args[0]

    def __str__(self):
        return "DebounceException: " + str(self.time_left.total_seconds()) + " seconds left!"


class Debounce:
    def __init__(self, debounce: timedelta = timedelta(minutes=3), failed_value=...,
                 params: Iterable[Union[str, Tuple[str], Callable]] = tuple()):
        # TODO - Add an on_debounce callback to be called and returned on debounce
        self.debounce: timedelta = debounce
        self.failed_value: Any = failed_value
        self.last_called: datetime = datetime.fromtimestamp(0)
        self.params: Dict[Union[str, Tuple[str], Callable], Dict[Any, datetime]] = {}
        self.param_check_parameters: Dict[Callable, Iterable[str]] = {}  # lambda param_check parameter names
        # Btw, if you store the end times instead of the last called times, you can have param-specific debounces
        for param_check in params:
            self.params[param_check] = {}
            if isinstance(param_check, Callable):
                self.param_check_parameters[param_check] = inspect.signature(param_check).parameters.keys()

    def __call__(self, func: Callable):
        sig = inspect.signature(func)

        @functools.wraps(func)
        def new_func(*args, **kwargs):
            for param, prior_values in self.params.items():
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                if isinstance(param, str):
                    current_values = bound_args.arguments[param]
                elif isinstance(param, Iterable):
                    current_values = tuple([bound_args.arguments[p] for p in param])
                elif isinstance(param, Callable):
                    current_values = param(**{param_name: bound_args.arguments[param_name]
                                              for param_name in self.param_check_parameters[param]})
                else:
                    raise TypeError("Can only use strings, collections of strings, or functions for parameter checks")
                if current_values:
                    last_called = prior_values.get(current_values)
                    if last_called is not None:
                        # Debounce failed
                        if self.failed_value is ...:
                            raise DebounceException(self.debounce - (datetime.utcnow() - last_called))
                        else:
                            return self.failed_value
                    else:
                        prior_values[current_values] = datetime.utcnow()

                        async def reset_debounce():
                            await asyncio.sleep(self.debounce.total_seconds())
                            prior_values.pop(current_values, "")

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