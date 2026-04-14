from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx

from python.calendar_core import CalendarEvent

from ..base import CalendarSyncProvider, parse_remote_datetime
from ..models import ExternalCalendar, RemoteSyncBatch, SyncCursor


class OutlookCalendarProvider(CalendarSyncProvider):
    provider_name = "outlook"

    def __init__(
        self,
        *,
        access_token: str,
        client: httpx.Client | None = None,
        base_url: str = "https://graph.microsoft.com/v1.0",
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=10.0,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def list_calendars(self) -> list[ExternalCalendar]:
        response = self._client.get("/me/calendars")
        response.raise_for_status()
        payload = response.json()
        calendars = []
        for item in payload.get("value", []):
            calendars.append(
                ExternalCalendar(
                    provider=self.provider_name,
                    calendar_id=item["id"],
                    name=item.get("name", item["id"]),
                    is_primary=item.get("isDefaultCalendar", False),
                    timezone=item.get("timeZone", "UTC"),
                )
            )
        return calendars

    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        response = self._client.post(
            f"/me/calendars/{quote(calendar_id, safe='')}/events",
            json=self._event_payload(event),
        )
        response.raise_for_status()
        return response.json()["id"]

    def update_event(self, calendar_id: str, remote_event_id: str, event: CalendarEvent) -> None:
        response = self._client.patch(
            f"/me/calendars/{quote(calendar_id, safe='')}/events/{quote(remote_event_id, safe='')}",
            json=self._event_payload(event),
        )
        response.raise_for_status()

    def delete_event(self, calendar_id: str, remote_event_id: str) -> None:
        response = self._client.delete(
            f"/me/calendars/{quote(calendar_id, safe='')}/events/{quote(remote_event_id, safe='')}"
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
        if cursor and cursor.value:
            response = self._client.get(cursor.value)
        else:
            params: dict[str, str] = {}
            if window_start is not None:
                params["startDateTime"] = window_start.isoformat()
            if window_end is not None:
                params["endDateTime"] = window_end.isoformat()
            response = self._client.get(
                f"/me/calendars/{quote(calendar_id, safe='')}/calendarView/delta",
                params=params,
            )
        response.raise_for_status()
        payload = response.json()

        active_events = []
        deleted_ids: list[str] = []
        for item in payload.get("value", []):
            removed = item.get("@removed")
            if removed:
                deleted_ids.append(item["id"])
                continue
            active_events.append(self._to_event(item))

        next_link = payload.get("@odata.deltaLink") or payload.get("@odata.nextLink")
        next_cursor = SyncCursor(provider=self.provider_name, value=next_link) if next_link else None
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
        body_preview = payload.get("bodyPreview") or ""
        return CalendarEvent(
            id=str(payload["id"]),
            title=str(payload.get("subject") or "Untitled event"),
            starts_at=starts_at,
            ends_at=ends_at,
            timezone=timezone,
            description=str(body_preview),
            location=str((payload.get("location") or {}).get("displayName", "")),
            metadata={"provider": self.provider_name},
        )

    def _event_payload(self, event: CalendarEvent) -> dict[str, object]:
        return {
            "subject": event.title,
            "body": {
                "contentType": "text",
                "content": event.description,
            },
            "location": {"displayName": event.location},
            "start": {
                "dateTime": event.starts_at.isoformat(),
                "timeZone": event.timezone,
            },
            "end": {
                "dateTime": event.ends_at.isoformat(),
                "timeZone": event.timezone,
            },
        }
