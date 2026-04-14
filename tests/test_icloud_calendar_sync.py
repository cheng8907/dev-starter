from __future__ import annotations

from datetime import UTC, datetime

import httpx

from python.calendar_core import CalendarEventInput, CalendarService, InMemoryCalendarRepository
from python.calendar_sync import CalendarSyncService
from python.calendar_sync.providers import ICloudCalendarProvider

DAV_NS = "DAV:"
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 14, hour, minute, tzinfo=UTC)


def build_icloud_provider() -> ICloudCalendarProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PROPFIND" and request.url.path == "/12345/calendars/":
            return httpx.Response(
                207,
                text="""<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/12345/calendars/</d:href>
    <d:propstat><d:prop><d:displayname>Home</d:displayname></d:prop></d:propstat>
  </d:response>
  <d:response>
    <d:href>/12345/calendars/home/</d:href>
    <d:propstat><d:prop><d:displayname>Home</d:displayname></d:prop></d:propstat>
  </d:response>
</d:multistatus>
""",
            )
        if request.method == "PUT" and request.url.path.startswith("/12345/calendars/home/"):
            assert "BEGIN:VCALENDAR" in request.content.decode()
            return httpx.Response(201)
        if request.method == "REPORT" and request.url.path == "/12345/calendars/home/":
            return httpx.Response(
                207,
                text="""<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/12345/calendars/home/remote-event.ics</d:href>
    <d:propstat>
      <d:prop>
        <c:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:remote-event
DTSTAMP:20260414T000000Z
DTSTART:20260414T090000Z
DTEND:20260414T100000Z
SUMMARY:iCloud Breakfast
DESCRIPTION:Shared across Apple devices
LOCATION:Kitchen
END:VEVENT
END:VCALENDAR</c:calendar-data>
      </d:prop>
    </d:propstat>
  </d:response>
</d:multistatus>
""",
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="https://caldav.icloud.com",
        transport=httpx.MockTransport(handler),
        auth=("user@example.com", "app-password"),
    )
    return ICloudCalendarProvider(
        username="user@example.com",
        app_specific_password="app-password",
        calendar_home_url="/12345/calendars/",
        default_calendar_url="https://caldav.icloud.com/12345/calendars/home/",
        client=client,
    )


def test_icloud_provider_lists_calendars() -> None:
    provider = build_icloud_provider()

    calendars = provider.list_calendars()

    assert len(calendars) == 1
    assert calendars[0].provider == "icloud"
    assert calendars[0].calendar_id.endswith("/12345/calendars/home/")


def test_icloud_provider_creates_calendar_object() -> None:
    provider = build_icloud_provider()
    repository = InMemoryCalendarRepository()
    calendar_service = CalendarService(repository)
    sync_service = CalendarSyncService(calendar_service)
    local_event = calendar_service.create_event(
        CalendarEventInput(
            title="Apple sync test",
            starts_at=dt(12),
            ends_at=dt(13),
            description="Write through CalDAV",
        )
    )

    pair = sync_service.push_event(
        provider,
        calendar_id="https://caldav.icloud.com/12345/calendars/home/",
        local_event_id=local_event.id,
    )

    assert pair.provider == "icloud"
    assert pair.remote_event_id.endswith(".ics")


def test_icloud_provider_pulls_remote_events() -> None:
    provider = build_icloud_provider()
    repository = InMemoryCalendarRepository()
    calendar_service = CalendarService(repository)
    sync_service = CalendarSyncService(calendar_service)

    result = sync_service.pull_events(
        provider,
        calendar_id="https://caldav.icloud.com/12345/calendars/home/",
        window_start=dt(0),
        window_end=dt(23, 59),
    )

    events = calendar_service.list_events()
    assert len(events) == 1
    assert events[0].title == "iCloud Breakfast"
    assert result.created[0].provider == "icloud"
