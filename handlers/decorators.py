from re import Pattern
from typing import Callable

from telegram.ext.filters import BaseFilter

from .base import HandlerObject
from .handlers import CallbackQuery, Command, Message, Startup
from inner_types import AsyncCallable


def startup(coro: AsyncCallable | None = None) -> Callable[..., Startup] | Startup:
    def wrapper(coro: AsyncCallable) -> Startup:
        return Startup(coro)

    if coro is not None:
        return wrapper(coro)

    return wrapper


def command(
    name: str = None, description: str = "No description set.", register: bool = True
) -> Callable[..., Command]:
    def wrapper(coro: AsyncCallable) -> Command:
        return Command(name=name or coro.__name__, description=description, register=register, coro=coro)

    return wrapper


def message(filters: BaseFilter) -> Callable[..., Message]:
    def wrapper(coro: AsyncCallable) -> Message:
        return Message(filters=filters, coro=coro)

    return wrapper


def callback_query(pattern: str | Pattern[str]) -> Callable[..., CallbackQuery]:
    def wrapper(coro: AsyncCallable) -> CallbackQuery:
        return CallbackQuery(coro=coro, pattern=pattern)

    return wrapper


class State:
    def __init__(self, name: str, handler: HandlerObject):
        self.name = name
        self.handler = handler


def state(name: str):
    def wrapper(handler: HandlerObject):
        return State(name, handler)

    return wrapper