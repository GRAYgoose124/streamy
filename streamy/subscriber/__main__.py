from abc import ABC, abstractmethod
from typing import Callable, Literal, Optional
from dataclasses import dataclass, field


from ..event import Event


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

    def subscribe(self, event_stream: "EventStream", events: list[Event]):
        for event_type in events:
            self._generic_nested_sub_operation(event_stream, event_type, "subscribe")

    def unsubscribe(self, event_stream: "EventStream", events: list[Event]):
        for event_type in events:
            self._generic_nested_sub_operation(event_stream, event_type, "unsubscribe")

    def _generic_nested_sub_operation(
        self, event_stream, event_type, operation: Literal["subscribe", "unsubscribe"]
    ):
        if isinstance(event_type, list):
            for event in event_type:
                self._generic_nested_sub_operation(event_stream, event, operation)
        elif issubclass(event_type, Event):
            getattr(event_stream, operation)(event_type, self)

    def __repr__(self):
        return self.name


@dataclass
class Subscription:
    subscriber: Subscriber
    filter_fns: list[tuple[Callable, Callable[[Event], bool]]] = field(
        default_factory=list
    )
    callback_fns: Optional[list[Callable[[Event], None]]] = field(default_factory=list)
    reject_on_filter: bool = True
    reject_with_cb: bool = False
