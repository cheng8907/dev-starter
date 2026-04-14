from __future__ import annotations

from datetime import UTC, datetime

import httpx

from python.calendar_core import CalendarEventInput, CalendarService, InMemoryCalendarRepository
from python.calendar_sync import CalendarSyncService, GoogleCalendarProvider, OutlookCalendarProvider


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 14, hour, minute, tzinfo=UTC)


def build_google_provider() -> GoogleCalendarProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/calendar/v3/users/me/calendarList":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "primary",
                            "summary": "Primary",
                            "primary": True,
                            "timeZone": "UTC",
                        }
                    ]
                },
            )
        if request.method == "POST" and request.url.path == "/calendar/v3/calendars/primary/events":
            return httpx.Response(200, json={"id": "google-event-1"})
        if request.method == "GET" and request.url.path == "/calendar/v3/calendars/primary/events":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "google-remote-1",
                            "summary": "Google standup",
                            "description": "Remote event",
                            "location": "Meet",
                            "start": {"dateTime": dt(9).isoformat(), "timeZone": "UTC"},
                            "end": {"dateTime": dt(10).isoformat(), "timeZone": "UTC"},
                        }
                    ],
                    "nextSyncToken": "google-sync-token",
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="https://www.googleapis.com/calendar/v3",
        transport=httpx.MockTransport(handler),
    )
    return GoogleCalendarProvider(access_token="token", client=client)


def build_outlook_provider() -> OutlookCalendarProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v1.0/me/calendars":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "id": "outlook-calendar-1",
                            "name": "Calendar",
                            "isDefaultCalendar": True,
                            "timeZone": "UTC",
                        }
                    ]
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/v1.0/me/calendars/outlook-calendar-1/calendarView/delta"
        ):
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "id": "outlook-remote-1",
                            "subject": "Outlook planning",
                            "bodyPreview": "Plan quarter",
                            "location": {"displayName": "HQ"},
                            "start": {"dateTime": dt(13).isoformat(), "timeZone": "UTC"},
                            "end": {"dateTime": dt(14).isoformat(), "timeZone": "UTC"},
                        }
                    ],
                    "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta-token",
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="https://graph.microsoft.com/v1.0",
        transport=httpx.MockTransport(handler),
    )
    return OutlookCalendarProvider(access_token="token", client=client)


def test_google_provider_lists_calendars() -> None:
    provider = build_google_provider()

    calendars = provider.list_calendars()

    assert len(calendars) == 1
    assert calendars[0].calendar_id == "primary"
    assert calendars[0].is_primary is True


def test_sync_service_pushes_local_event_to_google() -> None:
    repository = InMemoryCalendarRepository()
    calendar_service = CalendarService(repository)
    sync_service = CalendarSyncService(calendar_service)
    provider = build_google_provider()

    local_event = calendar_service.create_event(
        CalendarEventInput(
            title="Ship sync module",
            starts_at=dt(15),
            ends_at=dt(16),
            description="Push local changes",
        )
    )

    pair = sync_service.push_event(
        provider,
        calendar_id="primary",
        local_event_id=local_event.id,
    )

    assert pair.local_event_id == local_event.id
    assert pair.remote_event_id == "google-event-1"
    assert pair.provider == "google"


def test_sync_service_pulls_google_events_into_local_repository() -> None:
    repository = InMemoryCalendarRepository()
    calendar_service = CalendarService(repository)
    sync_service = CalendarSyncService(calendar_service)
    provider = build_google_provider()

    result = sync_service.pull_events(
        provider,
        calendar_id="primary",
        window_start=dt(0),
        window_end=dt(23, 59),
    )

    events = calendar_service.list_events()
    assert len(events) == 1
    assert events[0].title == "Google standup"
    assert result.next_cursor is not None
    assert result.next_cursor.value == "google-sync-token"
    assert len(result.created) == 1


def test_repeated_pull_updates_existing_google_mapping_without_duplicates() -> None:
    repository = InMemoryCalendarRepository()
    calendar_service = CalendarService(repository)
    sync_service = CalendarSyncService(calendar_service)
    provider = build_google_provider()

    first_result = sync_service.pull_events(
        provider,
        calendar_id="primary",
        window_start=dt(0),
        window_end=dt(23, 59),
    )
    second_result = sync_service.pull_events(
        provider,
        calendar_id="primary",
        cursor=first_result.next_cursor,
    )

    events = calendar_service.list_events()
    assert len(events) == 1
    assert len(first_result.created) == 1
    assert len(second_result.updated) == 1


def test_outlook_provider_pulls_delta_events() -> None:
    repository = InMemoryCalendarRepository()
    calendar_service = CalendarService(repository)
    sync_service = CalendarSyncService(calendar_service)
    provider = build_outlook_provider()

    calendars = provider.list_calendars()
    result = sync_service.pull_events(
        provider,
        calendar_id=calendars[0].calendar_id,
        window_start=dt(0),
        window_end=dt(23, 59),
    )

    events = calendar_service.list_events()
    assert len(events) == 1
    assert events[0].title == "Outlook planning"
    assert result.next_cursor is not None
    assert result.next_cursor.value == "https://graph.microsoft.com/v1.0/delta-token"
