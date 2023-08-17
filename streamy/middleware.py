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

    @abstractmethod
    async def __call__(self, event):
        """Middleware function that can be overridden."""
        pass


class LoggerMiddleware(Middleware):
    """Middleware that logs all events."""

    def __init__(self, name=None):
        self.name = name
        super().__init__()

    def __post_init__(self):
        """Initialize the middleware."""
        print(f"Initializing {self.name} middleware.")
        # get the root logger
        if self.name:
            self.logger = logging.getLogger().getChild(self.name)
        else:
            self.logger = logging.getLogger()

    async def __call__(self, event):
        """Log the event."""
        self.logger.info(f"Event: {event}")
        return event
