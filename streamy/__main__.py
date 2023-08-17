import asyncio
from abc import ABC, abstractmethod
import logging
import random

from .stream import EventStream
from .event import Event
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
            await asyncio.sleep(random.randint(1, 5))
            event = MyEvent if random.randint(1, 2) == 1 else MyOtherEvent
            await self.event_stream.publish(event(random.randint(1, 100)))


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

    evdict = str_evdict_to_instanced(
        {
            MyEvent: ["A", "B"],
            MyOtherEvent: ["B", "C"],
        },
        MySubscriber,
    )
    stream = EventStream()
    stream.subscribe(evdict)

    await gather_eloops(*[MyPublisher(stream) for _ in range(3)], stream)


def main():
    logging.basicConfig(level=logging.DEBUG)

    try:
        asyncio.run(event_stream_demo())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
