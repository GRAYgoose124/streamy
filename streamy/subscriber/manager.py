from collections import defaultdict
from collections.abc import Mapping
import operator

from ..event import Event
from ..subscriber.__main__ import Subscriber, Subscription


class SubscriberManager:
    def __init__(self):
        self._subscriptions = defaultdict(list)

    def get_subscriptions_for_event(self, event_type):
        return self._subscriptions.get(event_type, [])

    def subscribe(self, event_type: Event | dict, subscriber=None, filter_fn=None):
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

    def subscribe_from(self, d: dict[Event | Subscriber, list[Event | Subscriber]]):
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

    # filters
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
