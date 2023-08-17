from abc import ABC, abstractmethod
from typing import Literal

from .event import Event


class Subscriber(ABC):
    def __init__(self, name):
        self.name = name
        self._idle = True

    @property
    def idle(self):
        """Waiting for events"""
        return self._idle

    @abstractmethod
    async def handler(self, event):
        pass

    async def __call__(self, events):
        self._idle = False
        for event in events:
            await self.handler(event)
        self._idle = True

    def subscribe(self, event_stream, event_type):
        self.generic_list_or_event(event_stream, event_type, "subscribe")

    def unsubscribe(self, event_stream, event_type):
        self.generic_list_or_event(event_stream, event_type, "unsubscribe")

    def generic_list_or_event(
        self, event_stream, event_type, operation: Literal["subscribe", "unsubscribe"]
    ):
        operation = getattr(event_stream, operation)

        if isinstance(event_type, list):
            for event in event_type:
                self.generic_list_or_event(event_stream, event, operation)
        elif issubclass(event_type, Event):
            operation(event_type, self)
