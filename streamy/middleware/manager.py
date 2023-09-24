from typing import Literal

from ..middleware.__main__ import Middleware


class MiddlewareManager:
    def __init__(self):
        self._middlewares = []

    def add_middleware(self, middleware: Middleware):
        middleware.event_stream = self
        self._middlewares.append(middleware)

    async def apply_middlewares(
        self, event, when: Literal["before", "after"] = "before"
    ):
        """Apply middlewares to the event."""
        for middleware in self._middlewares:
            if when == "before":
                event = await middleware.pre(event)
            elif when == "after":
                event = await middleware.post(event)

            if event is None:
                return None
        return event
