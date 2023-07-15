from telegram.ext import ConversationHandler

from handlers.base import HandlerObject


class Conversation:
    class States:
        END = ConversationHandler.END
        TIMEOUT = ConversationHandler.TIMEOUT
        WAITING = ConversationHandler.WAITING

        @classmethod
        def generate_state(cls, length: int):
            return map(str, range(length))

    def __init__(self):
        self._entry_points: list = []
        self._states: dict[str, list[HandlerObject]] = {}
        self._fallbacks = []

    def entry_point(self):
        def wrapper(handler: HandlerObject):
            self._entry_points.append(handler)
        return wrapper

    def state(self, name: str):
        def wrapper(handler: HandlerObject):
            if name not in self._states:
                self._states[name] = [handler]
            else:
                self._states[name].append(handler)

        return wrapper

    def fallback(self):
        def wrapper(handler: HandlerObject):
            self._fallbacks.append(handler)
        return wrapper

    def as_handler(self):
        return ConversationHandler(
            entry_points=[entry_point.handler for entry_point in self._entry_points],
            states={name: [state.handler for state in states] for name, states in self._states.items()},
            fallbacks=[fallback.handler for fallback in self._fallbacks]
        )
