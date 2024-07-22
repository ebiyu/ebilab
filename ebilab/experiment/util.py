from typing import TypeVar, Generic, Callable

T = TypeVar("T")


class Event(Generic[T]):
    """
    Event management class
    """

    def __init__(self) -> None:
        self.event_listeners: list[Callable[[T], None]] = []

    def add_listener(self, listener: Callable[[T], None]) -> None:
        self.event_listeners.append(listener)

    def notify(self, event: T) -> None:
        for listener in self.event_listeners:
            listener(event)
