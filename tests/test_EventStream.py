import asyncio
import pytest
import logging

from streamy import *
from streamy.middleware.basic import LoggerMiddleware


log = logging.getLogger(__name__)


pytest_plugins = ("asyncio",)


# pytest log setup
@pytest.fixture(autouse=True)
def setup_logging(caplog):
    logging.basicConfig(level=logging.DEBUG)
    caplog.set_level(logging.DEBUG)


class _TestEvent(Event):
    pass


class _TestPublisher(Publisher):
    async def loop(self):
        await self.event_stream.publish(_TestEvent("test_data"))
        log.debug(f"{self} published {_TestEvent}")


class _TestSubscriber(Subscriber):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_data = None

    async def handler(self, event):
        log.debug(f"{self} received {event}")
        self.received_data = event.data


@pytest.mark.asyncio
async def test_publisher_subscriber_interaction():
    stream = EventStream()
    subscriber = _TestSubscriber(name="TestSubscriber")
    subscriber.subscribe(stream, events=[_TestEvent])
    # stream.subscribe(_TestEvent, subscriber=subscriber) # this can also be used with EventMappings

    await asyncio.gather(_TestPublisher(stream).loop(), stream._dispatch_all(False))

    assert subscriber.received_data == "test_data"


class StopMiddleware(Middleware):
    async def pre(self, event):
        return None  # Stop propagation


@pytest.mark.asyncio
async def test_middleware_processing():
    stream = EventStream()
    stream.add_middleware(StopMiddleware())
    subscriber = _TestSubscriber(name="TestSubscriber")
    stream.subscribe(_TestEvent, subscriber=subscriber)
    publisher = _TestPublisher(stream)
    await publisher.loop()  # Run the loop once to publish an event
    await stream._dispatch_all()

    # Because the middleware stopped propagation
    assert subscriber.received_data is None


@pytest.mark.asyncio
async def test_event_filters():
    stream = EventStream()
    stream.add_middleware(LoggerMiddleware(name="Logger"))
    subscriber = _TestSubscriber(name="TestSubscriber")
    stream.subscribe(_TestEvent, subscriber=subscriber)
    stream.update_filter(lambda e: e.data != "allow", subscriber_name="TestSubscriber")
    publisher = _TestPublisher(stream)
    await publisher.loop()  # Run the loop once to publish an event with "test_data"
    await stream._dispatch_all()

    # Because the filter did not match
    assert subscriber.received_data is None


if __name__ == "__main__":
    pytest.main()
