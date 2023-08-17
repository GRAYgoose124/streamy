from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

from .event import Event


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


class LoggerMiddleware(Middleware):
    """Middleware that logs all events."""

    def __init__(self, name=None):
        self.name = name
        super().__init__()

    def __post_init__(self):
        """Initialize the middleware."""
        if self.name:
            self.logger = logging.getLogger().getChild(self.name)
        else:
            self.logger = logging.getLogger()

    async def pre(self, event):
        """Log the event."""
        self.logger.info(f"Event: {event}")
        return event


class ContextMiddleware(Middleware):
    """Middleware that adds a context to the event."""

    def __init__(self, context=None):
        self.context = context
        super().__init__()

    async def pre(self, event):
        """Add the context to the event."""
        event.context = self.context
        return event
