from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .models import CalendarEvent


class CalendarRepository(Protocol):
    def add(self, event: CalendarEvent) -> CalendarEvent: ...

    def get(self, event_id: str) -> CalendarEvent | None: ...

    def list(self) -> list[CalendarEvent]: ...

    def update(self, event: CalendarEvent) -> CalendarEvent: ...

    def delete(self, event_id: str) -> bool: ...


class InMemoryCalendarRepository:
    def __init__(self, events: Iterable[CalendarEvent] | None = None) -> None:
        self._events: dict[str, CalendarEvent] = {}
        for event in events or ():
            self._events[event.id] = event

    def add(self, event: CalendarEvent) -> CalendarEvent:
        if event.id in self._events:
            raise ValueError(f"event {event.id} already exists")
        self._events[event.id] = event
        return event

    def get(self, event_id: str) -> CalendarEvent | None:
        return self._events.get(event_id)

    def list(self) -> list[CalendarEvent]:
        return sorted(self._events.values(), key=lambda event: (event.starts_at, event.id))

    def update(self, event: CalendarEvent) -> CalendarEvent:
        if event.id not in self._events:
            raise KeyError(f"event {event.id} does not exist")
        self._events[event.id] = event
        return event

    def delete(self, event_id: str) -> bool:
        return self._events.pop(event_id, None) is not None
