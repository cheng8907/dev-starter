from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from python.calendar_core import CalendarEvent

from .models import ExternalCalendar, RemoteSyncBatch, SyncCursor


def parse_remote_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    result = datetime.fromisoformat(normalized)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("remote datetime values must be timezone-aware")
    return result.astimezone(UTC)


class CalendarSyncProvider(ABC):
    provider_name: str

    @abstractmethod
    def list_calendars(self) -> list[ExternalCalendar]:
        raise NotImplementedError

    @abstractmethod
    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        raise NotImplementedError

    @abstractmethod
    def update_event(self, calendar_id: str, remote_event_id: str, event: CalendarEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_event(self, calendar_id: str, remote_event_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def pull_changes(
        self,
        calendar_id: str,
        *,
        cursor: SyncCursor | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> RemoteSyncBatch:
        raise NotImplementedError
