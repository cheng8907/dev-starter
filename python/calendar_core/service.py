from __future__ import annotations

from datetime import datetime

from .models import CalendarEvent, CalendarEventInput, CalendarEventUpdate
from .storage import CalendarRepository


class CalendarService:
    def __init__(self, repository: CalendarRepository) -> None:
        self.repository = repository

    def create_event(self, event_input: CalendarEventInput) -> CalendarEvent:
        event = event_input.to_event()
        self._ensure_no_conflicts(event)
        return self.repository.add(event)

    def get_event(self, event_id: str) -> CalendarEvent | None:
        return self.repository.get(event_id)

    def list_events(self) -> list[CalendarEvent]:
        return self.repository.list()

    def list_events_in_range(
        self,
        range_start: datetime,
        range_end: datetime,
    ) -> list[CalendarEvent]:
        return [
            event
            for event in self.repository.list()
            if event.occurs_within(range_start, range_end)
        ]

    def update_event(self, event_id: str, event_update: CalendarEventUpdate) -> CalendarEvent:
        existing = self._get_required_event(event_id)
        updated = event_update.apply_to(existing)
        self._ensure_no_conflicts(updated, ignored_event_id=event_id)
        return self.repository.update(updated)

    def delete_event(self, event_id: str) -> bool:
        return self.repository.delete(event_id)

    def find_conflicts(self, candidate: CalendarEvent) -> list[CalendarEvent]:
        return [
            event
            for event in self.repository.list()
            if event.id != candidate.id and event.overlaps(candidate)
        ]

    def _ensure_no_conflicts(
        self,
        candidate: CalendarEvent,
        *,
        ignored_event_id: str | None = None,
    ) -> None:
        conflicts = [
            event
            for event in self.repository.list()
            if event.id != ignored_event_id and event.id != candidate.id and event.overlaps(candidate)
        ]
        if conflicts:
            conflict_ids = ", ".join(event.id for event in conflicts)
            raise ValueError(f"event conflicts with existing events: {conflict_ids}")

    def _get_required_event(self, event_id: str) -> CalendarEvent:
        event = self.repository.get(event_id)
        if event is None:
            raise KeyError(f"event {event_id} does not exist")
        return event
