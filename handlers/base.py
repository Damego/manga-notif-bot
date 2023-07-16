from inner_types import AsyncCallable


class HandlerObject:
    def __init__(self, coro: AsyncCallable):
        self.coro = coro
