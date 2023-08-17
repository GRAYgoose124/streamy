import asyncio
from abc import ABC, abstractmethod
import logging
import random

from streamy.middleware import LoggerMiddleware

from .stream import EventStream
from .event import ELoop, Event
from .publisher import Publisher
from .subscriber import Subscriber
from .utils import eloop_gather, instanced_evdict


log = logging.getLogger(__name__)


class MyEvent(Event):
    pass


class MyOtherEvent(Event):
    pass


class MySubscriber(Subscriber):
    async def handler(self, event):
        print(f"{self.name} received {event}")


class MyPublisher(Publisher):
    async def loop(self):
        while True:
            event_cls = MyEvent if random.randint(0, 1) == 1 else MyOtherEvent
            await self.event_stream.publish(event_cls(random.randint(1, 100)))
            await asyncio.sleep(random.uniform(0.1, 0.5))


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(module)s:%(lineno)d\t%(levelname)s] %(message)s",
    )

    stream = EventStream()
    stream.add_middleware(LoggerMiddleware(name="Logger"))
    stream.subscribe(
        instanced_evdict(
            {
                MyEvent: ["A", "B"],
                MyOtherEvent: ["B", "C"],
            },
            MySubscriber,
        )
    )
    stream.update_filter(lambda e: e.data % 2 == 0, event_type=MyEvent)
    stream.update_filter(lambda e: e.data % 2 == 1, subscriber_name="B")
    stream.update_filter(
        lambda e: e.data % 2 == 0, subscriber_name="C", callback_fns=[print]
    )

    try:
        asyncio.get_event_loop().run_until_complete(
            eloop_gather(*[MyPublisher(stream) for _ in range(3)], stream)
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
