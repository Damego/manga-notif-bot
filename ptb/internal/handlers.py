from re import Pattern

from telegram import BotCommand
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import BaseFilter

from .base import HandlerObject
from ..inner_types import AsyncCallable


class Command(HandlerObject):
    def __init__(
        self, *, name: str, description: str, register: bool, coro: AsyncCallable
    ):
        super().__init__(coro)

        self.handler = CommandHandler(name, coro)
        self.bot_command = BotCommand(name, description)
        self.register = register


class Startup(HandlerObject):
    ...


class Message(HandlerObject):
    def __init__(self, *, filters: BaseFilter, coro: AsyncCallable):
        super().__init__(coro)

        self.handler = MessageHandler(filters, coro)


class CallbackQuery(HandlerObject):
    def __init__(self, *, pattern: str | Pattern[str], coro: AsyncCallable):
        super().__init__(coro)

        self.handler = CallbackQueryHandler(coro, pattern)
