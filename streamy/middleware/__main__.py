from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

from ..event import Event


class Middleware(ABC):
    """Base class for middleware, which is any arbitrary code that can be run before
    or after an event publish and subscribe.

    It can be used to add additional functionality to the event system,
    such as logging or authorization.
    """

    def __init__(self):
        """Initialize the middleware."""
        self._event_stream = None
        self.__post_init__()

    def __post_init__(self):
        pass

    @property
    def event_stream(self):
        """Get the event stream."""
        return self._event_stream

    @event_stream.setter
    def event_stream(self, event_stream):
        """Set the event stream."""
        self._event_stream = event_stream

    async def pre(self, event):
        """Middleware function that can be overridden."""
        return event

    async def post(self, event):
        """Middleware function that can be overridden."""
        return event
