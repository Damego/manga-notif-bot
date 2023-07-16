import asyncio
import inspect
import sys

from telegram import Bot
from telegram.ext import ApplicationBuilder, Application

from handlers.handlers import Command, Startup
from handlers.conversation import Conversation
from handlers.base import HandlerObject

__all__ = ("Client",)


class Client:
    def __init__(self):
        self.__app_builder = ApplicationBuilder()
        self.app: Application | None = None
        self._commands: list[Command] = []
        self._handlers: list[HandlerObject] = []
        self._startup_handlers: list[HandlerObject] = []

    @property
    def bot(self) -> Bot:
        return self.app.bot

    @property
    def job_queue(self):
        return self.app.job_queue

    def __register_handlers(self):
        self._handlers = [
            handler
            for _, handler in inspect.getmembers(sys.modules["__main__"])
            if isinstance(handler, (HandlerObject, Conversation))
        ]

        self._commands: list[Command] = [
            cmd for cmd in self._handlers if isinstance(cmd, Command)
        ]

        self.app.add_handlers(
            [
                handler.handler
                for handler in self._handlers
                if hasattr(handler, "handler")
            ]
        )

        self._startup_handlers = [
            handler for handler in self._handlers if isinstance(handler, Startup)
        ]

        conversation_handlers = [
            conv.as_handler()
            for conv in self._handlers
            if isinstance(conv, Conversation)
        ]
        print(conversation_handlers[0].states["1"][0].callback)
        self.app.add_handlers(conversation_handlers)

    async def post_init(self, application: Application):
        await application.bot.set_my_commands(
            [cmd.bot_command for cmd in self._commands if cmd.register]
        )

        for handler in self._startup_handlers:
            asyncio.create_task(handler.coro())

    def run(self, token: str):
        self.app = self.__app_builder.token(token).post_init(self.post_init).build()

        self.__register_handlers()

        self.app.run_polling()
