import asyncio
import pytest

from streamy.middleware import LoggerMiddleware, Middleware
from streamy.stream import EventStream
from streamy.event import Event
from streamy.publisher import Publisher
from streamy.subscriber import Subscriber

pytest_plugins = ("asyncio",)


class _TestEvent(Event):
    pass


class _TestPublisher(Publisher):
    async def loop(self):
        await self.event_stream.publish(_TestEvent("test_data"))


class _TestSubscriber(Subscriber):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_data = None

    async def handler(self, event):
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
    assert (
        subscriber.received_data is None
    )  # Because the middleware stopped propagation


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

    assert subscriber.received_data is None  # Because the filter did not match


if __name__ == "__main__":
    pytest.main()
