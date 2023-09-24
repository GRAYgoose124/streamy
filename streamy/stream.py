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
from .subscriber import SubscriberManager, Subscriber
from .middleware import MiddlewareManager

log = logging.getLogger(__name__)


class EventStream(ELoop, MiddlewareManager, SubscriberManager):
    # BaseSubscriber = Subscriber
    # BaseEvent = Event

    def __init__(self):
        ELoop.__init__(self, self)
        MiddlewareManager.__init__(self)
        SubscriberManager.__init__(self)

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

    # TODO: middlewares shouldn't be tied into the event stream
    async def publish(self, event, middleware=True):
        if middleware:
            # TODO: Apply before event without coupling to EventStream
            event = await self.apply_middlewares(event, when="before")
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
            # maybe kinda useless? TODO: Apply after event but w/o coupling to EventStream
            for event in events:
                await self.apply_middlewares(event, when="after")
        except Exception as e:
            log.error(
                f"Error in subscriber {subscriber.name}:\n{traceback.format_exc()}\n"
            )
        finally:
            self._active_subscribers -= 1

    @classmethod
    def from_dict(cls, evs: dict[Subscriber | Event, list[Event | Subscriber]]):
        stream = cls()
        stream.subscribe(evs)
        return stream
