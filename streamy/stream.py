import asyncio
from functools import singledispatch
import logging
from collections import defaultdict
from collections.abc import Mapping
from typing import Dict

from .event import ELoop, Event
from .subscriber import Subscriber

log = logging.getLogger(__name__)


class EventStream(ELoop):
    # BaseSubscriber = Subscriber
    # BaseEvent = Event

    def __init__(self):
        self._subscriptions = defaultdict(list)
        self._event_queue = asyncio.Queue()
        self._done = False
        self._active_subscribers = 0

    @property
    def idle(self):
        """Waiting for events"""
        return self._event_queue.empty() and self._active_subscribers == 0

    @property
    def done(self):
        """Finished"""
        return self._done

    def subscribe(self, event_type, subscriber=None):
        if subscriber is None:
            if isinstance(event_type, Mapping):
                return self.subscribe_from(event_type)
            else:
                raise TypeError(
                    "subscriber must be specified if event_type is not a mapping"
                )

        self._subscriptions[event_type].append(subscriber)

    def unsubscribe(self, event_type, subscriber):
        self._subscriptions[event_type].remove(subscriber)

    def unsubscribe_all(self, subscriber):
        for _, subscribers in self._subscriptions.items():
            if subscriber in subscribers:
                subscribers.remove(subscriber)

    async def publish(self, event):
        await self._event_queue.put(event)

    async def loop(self):
        """Dispatch loop"""
        while not self.done:
            try:
                await self._dispatch_all()
            except KeyboardInterrupt:
                self._done = True
            except Exception as e:
                log.error(f"Error during dispatch: {e}")

            await asyncio.sleep(1)

    async def _dispatch_all(self):
        while not self._event_queue.empty():
            event = await self._event_queue.get()
            subscribers = self._subscriptions[type(event)]
            tasks = [
                self._safe_dispatch(subscriber, [event]) for subscriber in subscribers
            ]
            await asyncio.gather(*tasks)

    async def _safe_dispatch(self, subscriber, events):
        try:
            self._active_subscribers += 1
            await subscriber(events)
        except Exception as e:
            log.error(f"Error in subscriber {subscriber.name}: {e}")
        finally:
            self._active_subscribers -= 1

    def subscribe_from(self, d: Dict[Event | Subscriber, list[Event | Subscriber]]):
        key_type = d.keys().__iter__().__next__()
        if issubclass(key_type, Event):
            for ev, subs in d.items():
                for sub in subs:
                    self.subscribe(ev, sub)
        elif issubclass(key_type, Subscriber):
            for sub, evs in d.items():
                for ev in evs:
                    self.subscribe(ev, sub)

    @classmethod
    def from_dict(cls, evs: dict[Subscriber | Event, list[Event | Subscriber]]):
        stream = cls()
        stream.subscribe(evs)
        return stream
