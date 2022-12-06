from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, TypeVar

from .impl import Interaction, Message

if TYPE_CHECKING:
    from .client import Client


EventT = TypeVar("EventT")
T = TypeVar("T")
Func = Callable[..., T]
CoroFunc = Func[Coroutine[Any, Any, Any]]

_log = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, bot: Client):
        self.events: Dict[str, List[CoroFunc]] = {}
        self.bot = bot

    def filter_events(self, event_type: EventT, event_data=None):
        if event_type in ("message_create", "message_update"):
            if event_type == "message_update" and len(event_data) == 4:
                return

            return Message(event_data)

        elif event_type == "interaction_create":
            return Interaction(self.bot, event_data)

        elif event_type == "ready":
            return None

        return event_data

    def add_callback(self, event_name, func: CoroFunc):
        if event_name not in self.events:
            raise ValueError("Event not in any known events!")

        self.events[event_name].append(func)

    def add_event(self, event_name: str):
        self.events[event_name] = []

    def subscribe(self, event_name: str, func: CoroFunc):
        self.events[event_name] = [func]

        _log.info("Subscribed to %r", event_name)

    def get_event(self, event_name: str):
        return self.events.get(event_name)

    def dispatch(self, event_name: str, *args, **kwargs):
        if not self.get_event(event_name):
            raise ValueError("Event not in any events known :(")

        event = self.events.get(event_name)
        if args is None and kwargs is None:
            data = None
        else:
            data = self.filter_events(event_name, *args)

        if event is not None:
            for callback in event:
                if data is None:
                    asyncio.create_task(callback())
                else:
                    asyncio.create_task(callback(data))

            _log.info("Dispatched event %r", event_name)
