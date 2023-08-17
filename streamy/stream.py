import asyncio
from dataclasses import dataclass
from functools import singledispatch
import logging
from collections import defaultdict
from collections.abc import Mapping
import traceback
from typing import Callable, Dict, NamedTuple

from .event import ELoop, Event
from .subscriber import Subscriber
from .middleware import Middleware

log = logging.getLogger(__name__)


@dataclass
class Subscription:
    subscriber: Subscriber
    filter_fn: Callable[[Event], bool] = None
    callback_fn: Callable[[Event], None] = None
    reject_on_filter: bool = True
    reject_with_cb: bool = False


class EventStream(ELoop):
    # BaseSubscriber = Subscriber
    # BaseEvent = Event

    def __init__(self):
        self._subscriptions = defaultdict(list)
        self._event_queue = asyncio.Queue()
        self._done = False
        self._active_subscribers = 0

        self._middlewares = []

    @property
    def idle(self):
        """Waiting for events"""
        return self._event_queue.empty() and self._active_subscribers == 0

    @property
    def done(self):
        """Finished"""
        return self._done

    async def publish(self, event, middleware=True):
        if middleware:
            event = await self._apply_middlewares(event)
            if event is None:
                return

        await self._event_queue.put(event)

    async def loop(self):
        """Dispatch loop"""
        while not self.done:
            try:
                await self._dispatch_all()
            except KeyboardInterrupt:
                self._done = True

            await asyncio.sleep(1)

    async def _dispatch_all(self, middleware=True):
        events = []
        while not self._event_queue.empty():
            event = await self._event_queue.get()
            if middleware:
                event = await self._apply_middlewares(event)
                if event is None:
                    continue
            events.append(event)

        tasks = []
        for event in events:
            subscriptions = self._subscriptions[type(event)]
            for subscription in subscriptions:
                if not subscription.filter_fn or subscription.filter_fn(event):
                    if subscription.callback_fn:
                        subscription.callback_fn(event)
                    if subscription.reject_on_filter:
                        if subscription.reject_with_cb or not subscription.callback_fn:
                            continue

                    tasks.append(self._safe_dispatch(subscription.subscriber, [event]))

        await asyncio.gather(*tasks)

    async def _safe_dispatch(self, subscriber, events):
        try:
            self._active_subscribers += 1
            await subscriber(events)
        except Exception as e:
            log.error(
                f"Error in subscriber {subscriber.name}:\n{traceback.format_exc()}\n"
            )
        finally:
            self._active_subscribers -= 1

    # middleware
    def add_middleware(self, middleware: Middleware):
        middleware._event_stream = self
        self._middlewares.append(middleware)

    async def _apply_middlewares(self, event):
        """Apply middlewares to the event."""
        for middleware in self._middlewares:
            event = await middleware(event)
            if event is None:
                return None
        return event

    def remove_filter(self, subscriber_name, event_type):
        for et, subscription_list in self._subscriptions.items():
            for subscription in subscription_list:
                if subscription.subscriber.name == subscriber_name:
                    subscription.filter_fn = None
                if et == event_type:
                    subscription.filter_fn = None

    def update_filter(
        self, filter_fn, callback_fn=None, subscriber_name=None, event_type=None
    ):
        if subscriber_name is None and event_type is None:
            raise ValueError("Either subscriber or event_type must be specified")
        if subscriber_name is not None and event_type is not None:
            raise ValueError("Only one of subscriber or event_type can be specified")

        def new_filter(s):
            old_filter = s.filter_fn
            if old_filter is None:
                return filter_fn
            else:
                return lambda e: filter_fn(e) and old_filter(e)

        if event_type is not None:
            for subscription in self._subscriptions[event_type]:
                subscription.filter_fn = new_filter(subscription)
                subscription.callback_fn = callback_fn
        else:
            for subscription_list in self._subscriptions.values():
                for subscription in subscription_list:
                    if subscription.subscriber.name == subscriber_name:
                        # TODO: should be list[tuple[Filter, Callback]]
                        subscription.filter_fn = new_filter(subscription)
                        subscription.callback_fn = callback_fn

    # subscription
    def subscribe(self, event_type, subscriber=None, filter_fn=None):
        if subscriber is None:
            if isinstance(event_type, Mapping):
                return self.subscribe_from(event_type)
            else:
                raise TypeError(
                    "subscriber must be specified if event_type is not a mapping"
                )

        subscription = Subscription(subscriber, filter_fn)
        self._subscriptions[event_type].append(subscription)

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

    def unsubscribe(self, event_type, subscriber):
        to_remove = [
            i
            for i, subscription in enumerate(self._subscriptions[event_type])
            if subscription.subscriber == subscriber
        ]

        for i in to_remove:
            self._subscriptions[event_type].pop(i)

    def unsubscribe_all(self, subscriber):
        for event_type in self._subscriptions.keys():
            self.unsubscribe(event_type, subscriber)

    @classmethod
    def from_dict(cls, evs: dict[Subscriber | Event, list[Event | Subscriber]]):
        stream = cls()
        stream.subscribe(evs)
        return stream
