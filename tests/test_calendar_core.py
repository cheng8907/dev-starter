from __future__ import annotations

from datetime import UTC, datetime

import pytest

from python.calendar_core import (
    CalendarEvent,
    CalendarEventInput,
    CalendarEventUpdate,
    CalendarService,
    InMemoryCalendarRepository,
)


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 14, hour, minute, tzinfo=UTC)


def test_create_event_normalizes_timezone_aware_datetimes() -> None:
    service = CalendarService(InMemoryCalendarRepository())

    event = service.create_event(
        CalendarEventInput(
            title="Design review",
            starts_at=dt(9),
            ends_at=dt(10),
            timezone="UTC",
            description="Review module boundaries",
            location="Remote",
        )
    )

    assert event.title == "Design review"
    assert event.starts_at == dt(9)
    assert event.ends_at == dt(10)
    assert event.duration_seconds == 3600


def test_create_event_rejects_conflicts() -> None:
    service = CalendarService(InMemoryCalendarRepository())
    service.create_event(
        CalendarEventInput(
            title="Morning standup",
            starts_at=dt(9),
            ends_at=dt(10),
        )
    )

    with pytest.raises(ValueError, match="conflicts"):
        service.create_event(
            CalendarEventInput(
                title="Overlapping planning session",
                starts_at=dt(9, 30),
                ends_at=dt(10, 30),
            )
        )


def test_update_event_keeps_event_id_and_validates_conflicts() -> None:
    service = CalendarService(InMemoryCalendarRepository())
    first = service.create_event(
        CalendarEventInput(
            title="Session A",
            starts_at=dt(9),
            ends_at=dt(10),
        )
    )
    service.create_event(
        CalendarEventInput(
            title="Session B",
            starts_at=dt(11),
            ends_at=dt(12),
        )
    )

    with pytest.raises(ValueError, match="conflicts"):
        service.update_event(
            first.id,
            CalendarEventUpdate(
                starts_at=dt(11, 30),
                ends_at=dt(12, 30),
            ),
        )


def test_list_events_in_range_returns_overlapping_items_only() -> None:
    service = CalendarService(InMemoryCalendarRepository())
    first = service.create_event(
        CalendarEventInput(
            title="Breakfast",
            starts_at=dt(8),
            ends_at=dt(9),
        )
    )
    second = service.create_event(
        CalendarEventInput(
            title="Focus block",
            starts_at=dt(10),
            ends_at=dt(12),
        )
    )

    results = service.list_events_in_range(dt(8, 30), dt(10, 30))

    assert [event.id for event in results] == [first.id, second.id]


def test_delete_event_removes_existing_event() -> None:
    service = CalendarService(InMemoryCalendarRepository())
    event = service.create_event(
        CalendarEventInput(
            title="Cleanup",
            starts_at=dt(14),
            ends_at=dt(15),
        )
    )

    assert service.delete_event(event.id) is True
    assert service.get_event(event.id) is None


def test_event_requires_timezone_aware_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        CalendarEvent(
            id="event-1",
            title="Bad event",
            starts_at=datetime(2026, 4, 14, 9, 0),
            ends_at=datetime(2026, 4, 14, 10, 0),
        )
