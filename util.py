import functools
import threading
import builtins
import sys


stdout_lock = threading.Lock()


def use(lock: threading.Lock):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator


@use(stdout_lock)
def print(
    *values: object,
    sep: str = " ",
    end: str = "\n",
    flush: bool = True,
    file=sys.stdout,
):
    return builtins.print(*values, sep=sep, end=end, flush=flush, file=file)


def input(prompt: str):
    print(prompt, end="")
    return builtins.input()


def prompt_name(prompt: str) -> str:
    while (name := input(prompt)) == "":
        continue

    return name


def prompt_int(prompt: str, default: int = None) -> int:
    while True:
        data = input(prompt)

        if data.isdigit():
            return int(data)

        if data == "" and default is not None:
            return default
