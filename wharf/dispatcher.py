from __future__ import annotations
from typing import TypeVar, Callable, Coroutine, Any
import inspect
import logging
import asyncio

_log = logging.getLogger(__name__)
T = TypeVar("T")
Func = Callable[..., T]
CoroFunc = Func[Coroutine[Any, Any, Any]]

class Dispatcher:
    """An base for an simple event dispatcher"""

    def __init__(self):
        self.events: dict[str, list[CoroFunc]] = {}
    
    def add_event(self, event_name: str):
        self.events[event_name] = []
    
    def remove_event(self, event_name: str):
        self.events.pop(event_name)

    def get_event(self, event_name: str):
        event = self.events.get(event_name)
        return event

    def add_callback(self, event_name: str, func: CoroFunc):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Callback MUST be a coroutine, the callback provided is not one.")

        if event_name not in self.events:
            raise ValueError("Event not in any known events!")

        self.events[event_name].append(func)

        _log.info("Registered callback for event %s", event_name)

    def remove_callback(self, event_name: str, index: int):
        if event_name not in self.events:
            raise ValueError("Event not in any known events!")
        
        self.events[event_name].pop(index)
        
        _log.info("Removed callback from event %s", event_name)

        
    def dispatch(self, event_name: str, *args, **kwargs):
        if event_name not in self.events:
            raise ValueError("Event not in any events known :(")

        callbacks = self.events.get(event_name)

        for callback in callbacks:
            asyncio.create_task(callback(*args, **kwargs))

        _log.info("Dispatched event %s", event_name)