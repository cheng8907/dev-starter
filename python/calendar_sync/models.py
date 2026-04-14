from __future__ import annotations

from dataclasses import dataclass, field

from python.calendar_core import CalendarEvent


@dataclass(slots=True, frozen=True)
class ExternalCalendar:
    provider: str
    calendar_id: str
    name: str
    is_primary: bool = False
    timezone: str = "UTC"


@dataclass(slots=True, frozen=True)
class SyncCursor:
    provider: str
    value: str | None = None


@dataclass(slots=True, frozen=True)
class SyncPair:
    local_event_id: str
    remote_event_id: str
    calendar_id: str
    provider: str


@dataclass(slots=True, frozen=True)
class SyncResult:
    created: tuple[SyncPair, ...] = field(default_factory=tuple)
    updated: tuple[SyncPair, ...] = field(default_factory=tuple)
    deleted_remote_ids: tuple[str, ...] = field(default_factory=tuple)
    next_cursor: SyncCursor | None = None


@dataclass(slots=True, frozen=True)
class RemoteSyncBatch:
    events: tuple[CalendarEvent, ...]
    next_cursor: SyncCursor | None = None
    deleted_remote_ids: tuple[str, ...] = field(default_factory=tuple)
