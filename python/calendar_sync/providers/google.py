from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx

from python.calendar_core import CalendarEvent

from ..base import CalendarSyncProvider, parse_remote_datetime
from ..models import ExternalCalendar, RemoteSyncBatch, SyncCursor


class GoogleCalendarProvider(CalendarSyncProvider):
    provider_name = "google"

    def __init__(
        self,
        *,
        access_token: str,
        client: httpx.Client | None = None,
        base_url: str = "https://www.googleapis.com/calendar/v3",
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=10.0,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def list_calendars(self) -> list[ExternalCalendar]:
        response = self._client.get("/users/me/calendarList")
        response.raise_for_status()
        payload = response.json()
        calendars = []
        for item in payload.get("items", []):
            calendars.append(
                ExternalCalendar(
                    provider=self.provider_name,
                    calendar_id=item["id"],
                    name=item.get("summary", item["id"]),
                    is_primary=item.get("primary", False),
                    timezone=item.get("timeZone", "UTC"),
                )
            )
        return calendars

    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        response = self._client.post(
            f"/calendars/{quote(calendar_id, safe='')}/events",
            json=self._event_payload(event),
        )
        response.raise_for_status()
        return response.json()["id"]

    def update_event(self, calendar_id: str, remote_event_id: str, event: CalendarEvent) -> None:
        response = self._client.put(
            f"/calendars/{quote(calendar_id, safe='')}/events/{quote(remote_event_id, safe='')}",
            json=self._event_payload(event),
        )
        response.raise_for_status()

    def delete_event(self, calendar_id: str, remote_event_id: str) -> None:
        response = self._client.delete(
            f"/calendars/{quote(calendar_id, safe='')}/events/{quote(remote_event_id, safe='')}"
        )
        response.raise_for_status()

    def pull_changes(
        self,
        calendar_id: str,
        *,
        cursor: SyncCursor | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> RemoteSyncBatch:
        params: dict[str, str] = {"singleEvents": "true", "showDeleted": "true"}
        if cursor and cursor.value:
            params["syncToken"] = cursor.value
        else:
            if window_start is not None:
                params["timeMin"] = window_start.isoformat()
            if window_end is not None:
                params["timeMax"] = window_end.isoformat()

        response = self._client.get(
            f"/calendars/{quote(calendar_id, safe='')}/events",
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
        active_events = []
        deleted_ids: list[str] = []
        for item in payload.get("items", []):
            if item.get("status") == "cancelled":
                deleted_ids.append(item["id"])
                continue
            active_events.append(self._to_event(item))

        next_value = payload.get("nextSyncToken")
        next_cursor = SyncCursor(provider=self.provider_name, value=next_value) if next_value else None
        return RemoteSyncBatch(
            events=tuple(active_events),
            next_cursor=next_cursor,
            deleted_remote_ids=tuple(deleted_ids),
        )

    def _to_event(self, payload: dict[str, object]) -> CalendarEvent:
        start_data = payload["start"]
        end_data = payload["end"]
        assert isinstance(start_data, dict)
        assert isinstance(end_data, dict)
        starts_at = parse_remote_datetime(str(start_data["dateTime"]))
        ends_at = parse_remote_datetime(str(end_data["dateTime"]))
        timezone = str(start_data.get("timeZone") or end_data.get("timeZone") or "UTC")
        return CalendarEvent(
            id=str(payload["id"]),
            title=str(payload.get("summary") or "Untitled event"),
            starts_at=starts_at,
            ends_at=ends_at,
            timezone=timezone,
            description=str(payload.get("description") or ""),
            location=str(payload.get("location") or ""),
            metadata={"provider": self.provider_name},
        )

    def _event_payload(self, event: CalendarEvent) -> dict[str, object]:
        return {
            "summary": event.title,
            "description": event.description,
            "location": event.location,
            "start": {
                "dateTime": event.starts_at.isoformat(),
                "timeZone": event.timezone,
            },
            "end": {
                "dateTime": event.ends_at.isoformat(),
                "timeZone": event.timezone,
            },
        }
