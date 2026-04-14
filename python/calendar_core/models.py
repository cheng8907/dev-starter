from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime values must be timezone-aware")
    return value


def _normalize_datetime(value: datetime) -> datetime:
    return _ensure_timezone(value).astimezone(UTC)


@dataclass(slots=True, frozen=True)
class CalendarEvent:
    id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    timezone: str = "UTC"
    description: str = ""
    location: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        starts_at = _normalize_datetime(self.starts_at)
        ends_at = _normalize_datetime(self.ends_at)
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if ends_at <= starts_at:
            raise ValueError("ends_at must be later than starts_at")
        object.__setattr__(self, "starts_at", starts_at)
        object.__setattr__(self, "ends_at", ends_at)
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "location", self.location.strip())

    @property
    def duration_seconds(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds())

    def overlaps(self, other: "CalendarEvent") -> bool:
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at

    def occurs_within(self, window_start: datetime, window_end: datetime) -> bool:
        start = _normalize_datetime(window_start)
        end = _normalize_datetime(window_end)
        if end <= start:
            raise ValueError("window_end must be later than window_start")
        return self.starts_at < end and start < self.ends_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "timezone": self.timezone,
            "description": self.description,
            "location": self.location,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True, frozen=True)
class CalendarEventInput:
    title: str
    starts_at: datetime
    ends_at: datetime
    timezone: str = "UTC"
    description: str = ""
    location: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_event(self, *, event_id: str | None = None) -> CalendarEvent:
        return CalendarEvent(
            id=event_id or str(uuid4()),
            title=self.title,
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            timezone=self.timezone,
            description=self.description,
            location=self.location,
            metadata=dict(self.metadata),
        )


@dataclass(slots=True, frozen=True)
class CalendarEventUpdate:
    title: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    description: str | None = None
    location: str | None = None
    metadata: dict[str, Any] | None = None

    def apply_to(self, event: CalendarEvent) -> CalendarEvent:
        updates: dict[str, Any] = {}
        if self.title is not None:
            updates["title"] = self.title
        if self.starts_at is not None:
            updates["starts_at"] = self.starts_at
        if self.ends_at is not None:
            updates["ends_at"] = self.ends_at
        if self.timezone is not None:
            updates["timezone"] = self.timezone
        if self.description is not None:
            updates["description"] = self.description
        if self.location is not None:
            updates["location"] = self.location
        if self.metadata is not None:
            updates["metadata"] = dict(self.metadata)
        return replace(event, **updates)
