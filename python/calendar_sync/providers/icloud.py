from __future__ import annotations

import posixpath
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx

from python.calendar_core import CalendarEvent

from ..base import CalendarSyncProvider
from ..models import ExternalCalendar, RemoteSyncBatch, SyncCursor

DAV_NS = "DAV:"
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"


def _normalize_href(base_url: str, href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(base_url, href)


def _escape_ics_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace("\n", r"\n")


def _unescape_ics_text(value: str) -> str:
    return value.replace(r"\n", "\n").replace(r"\,", ",").replace(r"\;", ";").replace("\\\\", "\\")


def _fold_ics_lines(content: str) -> str:
    lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line
        while len(line.encode("utf-8")) > 70:
            chunk = line[:70]
            lines.append(chunk)
            line = f" {line[70:]}"
        lines.append(line)
    return "\r\n".join(lines) + "\r\n"


def _unfold_ics_lines(content: str) -> list[str]:
    unfolded: list[str] = []
    for line in content.replace("\r\n", "\n").split("\n"):
        if not line:
            continue
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _parse_ics_datetime(value: str, tzid: str | None = None) -> tuple[datetime, str]:
    if value.endswith("Z"):
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        return parsed, "UTC"
    parsed = datetime.strptime(value, "%Y%m%dT%H%M%S")
    timezone_name = tzid or "UTC"
    try:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    except Exception:
        parsed = parsed.replace(tzinfo=UTC)
        timezone_name = "UTC"
    return parsed.astimezone(UTC), timezone_name


class ICloudCalendarProvider(CalendarSyncProvider):
    provider_name = "icloud"

    def __init__(
        self,
        *,
        username: str,
        app_specific_password: str,
        calendar_home_url: str | None = None,
        default_calendar_url: str | None = None,
        client: httpx.Client | None = None,
        base_url: str = "https://caldav.icloud.com",
    ) -> None:
        if not calendar_home_url and not default_calendar_url:
            raise ValueError("calendar_home_url or default_calendar_url is required")
        self.base_url = base_url
        self.calendar_home_url = calendar_home_url
        self.default_calendar_url = default_calendar_url
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=15.0,
            auth=(username, app_specific_password),
            headers={"Content-Type": "application/xml; charset=utf-8"},
        )

    def list_calendars(self) -> list[ExternalCalendar]:
        if self.calendar_home_url is None and self.default_calendar_url is not None:
            return [
                ExternalCalendar(
                    provider=self.provider_name,
                    calendar_id=self.default_calendar_url,
                    name=self._calendar_name(self.default_calendar_url),
                    is_primary=True,
                    timezone="UTC",
                )
            ]

        body = """<?xml version="1.0" encoding="utf-8" ?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop>
    <d:displayname />
    <c:calendar-description />
    <c:supported-calendar-component-set />
  </d:prop>
</d:propfind>
"""
        response = self._client.request(
            "PROPFIND",
            self.calendar_home_url,
            headers={"Depth": "1"},
            content=body,
        )
        response.raise_for_status()
        calendars: list[ExternalCalendar] = []
        xml_root = ET.fromstring(response.text)
        for href, display_name in self._extract_calendar_nodes(xml_root):
            calendars.append(
                ExternalCalendar(
                    provider=self.provider_name,
                    calendar_id=_normalize_href(self.base_url, href),
                    name=display_name or self._calendar_name(href),
                    is_primary=len(calendars) == 0,
                    timezone="UTC",
                )
            )
        return calendars

    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        object_name = f"{uuid.uuid4()}.ics"
        event_href = self._event_url(calendar_id, object_name)
        response = self._client.put(
            event_href,
            headers={"Content-Type": "text/calendar; charset=utf-8"},
            content=self._serialize_event(event, uid=object_name.removesuffix(".ics")),
        )
        response.raise_for_status()
        return event_href

    def update_event(self, calendar_id: str, remote_event_id: str, event: CalendarEvent) -> None:
        event_href = self._event_url(calendar_id, remote_event_id)
        uid = posixpath.basename(urlparse(event_href).path).removesuffix(".ics") or event.id
        response = self._client.put(
            event_href,
            headers={"Content-Type": "text/calendar; charset=utf-8"},
            content=self._serialize_event(event, uid=uid),
        )
        response.raise_for_status()

    def delete_event(self, calendar_id: str, remote_event_id: str) -> None:
        response = self._client.delete(self._event_url(calendar_id, remote_event_id))
        response.raise_for_status()

    def pull_changes(
        self,
        calendar_id: str,
        *,
        cursor: SyncCursor | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> RemoteSyncBatch:
        del cursor
        start = (window_start or datetime.now(tz=UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        end = (window_end or datetime.now(tz=UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        body = f"""<?xml version="1.0" encoding="utf-8" ?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop>
    <d:getetag />
    <c:calendar-data />
  </d:prop>
  <c:filter>
    <c:comp-filter name="VCALENDAR">
      <c:comp-filter name="VEVENT">
        <c:time-range start="{start}" end="{end}" />
      </c:comp-filter>
    </c:comp-filter>
  </c:filter>
</c:calendar-query>
"""
        response = self._client.request(
            "REPORT",
            calendar_id,
            headers={"Depth": "1"},
            content=body,
        )
        response.raise_for_status()
        xml_root = ET.fromstring(response.text)
        events = []
        for href, calendar_data in self._extract_event_nodes(xml_root):
            if not calendar_data:
                continue
            event = self._parse_calendar_data(calendar_data, href)
            if event is not None:
                events.append(event)
        return RemoteSyncBatch(events=tuple(events), next_cursor=None, deleted_remote_ids=tuple())

    def _extract_calendar_nodes(self, root: ET.Element) -> list[tuple[str, str]]:
        responses = []
        for response in root.findall(f"{{{DAV_NS}}}response"):
            href = response.findtext(f"{{{DAV_NS}}}href") or ""
            display_name = response.findtext(f".//{{{DAV_NS}}}displayname") or ""
            if not href or href.rstrip("/") == (self.calendar_home_url or "").rstrip("/"):
                continue
            if href.endswith("/"):
                responses.append((href, display_name))
        return responses

    def _extract_event_nodes(self, root: ET.Element) -> list[tuple[str, str]]:
        nodes: list[tuple[str, str]] = []
        for response in root.findall(f"{{{DAV_NS}}}response"):
            href = response.findtext(f"{{{DAV_NS}}}href") or ""
            calendar_data = response.findtext(f".//{{{CALDAV_NS}}}calendar-data") or ""
            if href and calendar_data:
                nodes.append((_normalize_href(self.base_url, href), calendar_data))
        return nodes

    def _parse_calendar_data(self, calendar_data: str, href: str) -> CalendarEvent | None:
        values: dict[str, tuple[str, dict[str, str]]] = {}
        for line in _unfold_ics_lines(calendar_data):
            if ":" not in line:
                continue
            field, raw_value = line.split(":", 1)
            parts = field.split(";")
            key = parts[0]
            params: dict[str, str] = {}
            for param in parts[1:]:
                if "=" in param:
                    param_key, param_value = param.split("=", 1)
                    params[param_key] = param_value
            values[key] = (raw_value, params)

        if "DTSTART" not in values or "DTEND" not in values:
            return None
        start_value, start_params = values["DTSTART"]
        end_value, end_params = values["DTEND"]
        starts_at, timezone_name = _parse_ics_datetime(start_value, start_params.get("TZID"))
        ends_at, end_timezone = _parse_ics_datetime(end_value, end_params.get("TZID"))
        title = _unescape_ics_text(values.get("SUMMARY", ("Untitled event", {}))[0])
        description = _unescape_ics_text(values.get("DESCRIPTION", ("", {}))[0])
        location = _unescape_ics_text(values.get("LOCATION", ("", {}))[0])
        return CalendarEvent(
            id=href,
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            timezone=timezone_name or end_timezone or "UTC",
            description=description,
            location=location,
            metadata={"provider": self.provider_name},
        )

    def _serialize_event(self, event: CalendarEvent, *, uid: str) -> str:
        dtstamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        starts_at = event.starts_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        ends_at = event.ends_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        ics = "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//Dev Starter//Calendar Sync//EN",
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART:{starts_at}",
                f"DTEND:{ends_at}",
                f"SUMMARY:{_escape_ics_text(event.title)}",
                f"DESCRIPTION:{_escape_ics_text(event.description)}",
                f"LOCATION:{_escape_ics_text(event.location)}",
                "END:VEVENT",
                "END:VCALENDAR",
            ]
        )
        return _fold_ics_lines(ics)

    def _event_url(self, calendar_id: str, remote_event_id: str) -> str:
        if remote_event_id.startswith("http://") or remote_event_id.startswith("https://"):
            return remote_event_id
        if remote_event_id.endswith(".ics"):
            object_name = remote_event_id
        else:
            object_name = f"{remote_event_id}.ics"
        if calendar_id.endswith("/"):
            return f"{calendar_id}{object_name}"
        return f"{calendar_id}/{object_name}"

    def _calendar_name(self, value: str) -> str:
        name = posixpath.basename(urlparse(value).path.rstrip("/"))
        return re.sub(r"[-_]+", " ", name).strip().title() or "iCloud Calendar"
