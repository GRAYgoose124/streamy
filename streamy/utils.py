import asyncio


def instanced_evdict(strevdict, subscriber_cls):
    # first gather subs to create
    subs = set()
    for subs_list in strevdict.values():
        subs.update(subs_list)

    # then create instances
    subs = [subscriber_cls(sub) for sub in subs]

    # now replace strings with instances
    evdict = {}
    for event_cls, subs_list in strevdict.items():
        evdict[event_cls] = [sub for sub in subs if sub.name in subs_list]

    return evdict


def eloop_gather(*eloopables):
    return asyncio.gather(*[e.loop() for e in eloopables])
