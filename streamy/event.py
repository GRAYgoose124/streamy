from abc import ABC, abstractmethod


class ELoop(ABC):
    """A base class for all classes which are meant to run as gathered with other loops by a final main thread gather."""

    def __init__(self, stream):
        self.event_stream = stream

    @abstractmethod
    async def loop(self):
        pass

    def __call__(self):
        return self.loop()


class Event:
    def __init__(self, data):
        self.name = self.__class__.__name__
        self.data = data

    def __repr__(self):
        return f"{self.name}({self.data})"

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.data == other.data
