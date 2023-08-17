import asyncio
from dataclasses import dataclass, field
from functools import singledispatch
import logging
from collections import defaultdict
from collections.abc import Mapping
import operator
import traceback
from typing import Callable, Dict, Literal, NamedTuple, Optional

from .event import ELoop, Event
from .subscriber import Subscriber
from .middleware import Middleware

log = logging.getLogger(__name__)


@dataclass
class Subscription:
    subscriber: Subscriber
    filter_fns: list[tuple[callable, Callable[[Event], bool]]] = field(
        default_factory=list
    )
    callback_fns: Optional[list[Callable[[Event], None]]] = field(default_factory=list)
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
            event = await self._apply_middlewares(event, when="before")
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
            # if middleware:
            #     event = await self._apply_middlewares(event, when="after")
            #     if event is None:
            #         continue
            events.append(self._event_queue.get_nowait())

        tasks = []
        for event in events:
            subscriptions = self._subscriptions[type(event)]
            for subscription in subscriptions:
                filter_result = True

                if len(subscription.filter_fns):
                    for op, ffn in subscription.filter_fns:
                        filter_result = op(ffn(event), filter_result)

                if len(subscription.filter_fns) or filter_result:
                    if len(subscription.callback_fns):
                        log.debug("Running %s's callback fn...", subscription)
                        for cb in subscription.callback_fns:
                            cb(event)
                    if subscription.reject_on_filter:
                        if (
                            subscription.reject_with_cb
                            or not len(subscription.callback_fns)
                            and not subscription.reject_with_cb
                        ):
                            log.debug("Rejecting %s for %s", event, subscription)
                            continue

                    tasks.append(self._safe_dispatch(subscription.subscriber, [event]))

        await asyncio.gather(*tasks)

    async def _safe_dispatch(self, subscriber, events):
        try:
            self._active_subscribers += 1
            await subscriber(events)
            # maybe kinda useless?
            for event in events:
                self._apply_middlewares(event, when="after")
        except Exception as e:
            log.error(
                f"Error in subscriber {subscriber.name}:\n{traceback.format_exc()}\n"
            )
        finally:
            self._active_subscribers -= 1

    # middleware
    def add_middleware(self, middleware: Middleware):
        middleware.event_stream = self
        self._middlewares.append(middleware)

    async def _apply_middlewares(
        self, event, when: Literal["before", "after"] = "before"
    ):
        """Apply middlewares to the event."""
        for middleware in self._middlewares:
            if when == "before":
                event = await middleware.pre(event)
            elif when == "after":
                event = await middleware.post(event)

            if event is None:
                return None
        return event

    def remove_filter(self, subscriber_name, event_type):
        for et, subscription_list in self._subscriptions.items():
            for subscription in subscription_list:
                if subscription.subscriber.name == subscriber_name:
                    subscription.filter_fns.clear()
                if et == event_type:
                    subscription.filter_fns.clear()

    def update_filter(
        self,
        filter_fn,
        filter_op=operator.and_,
        callback_fns=None,
        subscriber_name=None,
        event_type=None,
    ):
        if subscriber_name is None and event_type is None:
            raise ValueError("Either subscriber or event_type must be specified")
        if subscriber_name is not None and event_type is not None:
            raise ValueError("Only one of subscriber or event_type can be specified")

        # TODO: Can probably fix this repetition
        if event_type is not None:
            for subscription in self._subscriptions[event_type]:
                subscription.filter_fns.append((filter_op, filter_fn))
                if callback_fns is not None:
                    subscription.callback_fns.extend(callback_fns)
        else:
            for subscription_list in self._subscriptions.values():
                for subscription in subscription_list:
                    if subscription.subscriber.name == subscriber_name:
                        subscription.filter_fns.append((filter_op, filter_fn))
                        if callback_fns is not None:
                            subscription.callback_fns.extend(callback_fns)

    # subscription
    def subscribe(self, event_type, subscriber=None, filter_fn=None):
        if subscriber is None:
            if isinstance(event_type, Mapping):
                return self.subscribe_from(event_type)
            else:
                raise TypeError(
                    "subscriber must be specified if event_type is not a mapping"
                )

        filter_fns = []
        if filter_fn:
            filter_fns.append(filter_fn)
        subscription = Subscription(subscriber, filter_fns)
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

    # def update_subscription()
