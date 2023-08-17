import asyncio
from abc import ABC, abstractmethod
import logging
import random

from streamy.middleware import LoggerMiddleware

from .stream import EventStream
from .event import ELoop, Event
from .publisher import Publisher
from .subscriber import Subscriber
from .utils import gather_eloops, str_evdict_to_instanced


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


async def event_stream_demo():
    # subs = {
    #     MySubscriber("A"): [MyEvent],
    #     MySubscriber("B"): [MyEvent, MyOtherEvent],
    #     MySubscriber("C"): [MyOtherEvent],
    # }
    # stream = EventStream.from_subdict(subs)

    # subs = {c: MySubscriber(c) for c in "ABC"}
    # evdict = {
    #     MyEvent: [subs["A"], subs["B"]],
    #     MyOtherEvent: [subs["B"], subs["C"]],
    # }
    # stream = EventStream.from_subdict(evdict)

    stream = EventStream()
    stream.add_middleware(LoggerMiddleware(name="Logger"))
    stream.subscribe(
        str_evdict_to_instanced(
            {
                MyEvent: ["A", "B"],
                MyOtherEvent: ["B", "C"],
            },
            MySubscriber,
        )
    )

    await gather_eloops(*[MyPublisher(stream) for _ in range(3)], stream)


def main():
    logging.basicConfig(level=logging.DEBUG)

    try:
        asyncio.run(event_stream_demo())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
