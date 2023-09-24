import logging
from pydantic import BaseModel, ValidationError, typing

from ..middleware import Middleware


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


class EventModel(BaseModel):
    name: str
    data: typing.Any


class PydanticMiddleware(Middleware):
    def __init__(self):
        super().__init__()

    async def post(self, event):
        """Validate the event using the Pydantic model."""
        try:
            validated_event = EventModel(**event.__dict__)

            return validated_event
        except ValidationError as e:
            # You can choose to log this, or handle it in a way that's suitable for your use-case
            pass
