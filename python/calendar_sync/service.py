from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from python.calendar_core import CalendarEvent, CalendarEventInput, CalendarService

from .base import CalendarSyncProvider
from .models import ExternalCalendar, SyncCursor, SyncPair, SyncResult


class CalendarSyncService:
    def __init__(self, calendar_service: CalendarService) -> None:
        self.calendar_service = calendar_service

    def list_remote_calendars(self, provider: CalendarSyncProvider) -> list[ExternalCalendar]:
        return provider.list_calendars()

    def push_event(
        self,
        provider: CalendarSyncProvider,
        *,
        calendar_id: str,
        local_event_id: str,
        remote_event_id: str | None = None,
    ) -> SyncPair:
        event = self._get_required_event(local_event_id)
        if remote_event_id:
            provider.update_event(calendar_id, remote_event_id, event)
            return SyncPair(
                local_event_id=event.id,
                remote_event_id=remote_event_id,
                calendar_id=calendar_id,
                provider=provider.provider_name,
            )

        created_remote_id = provider.create_event(calendar_id, event)
        return SyncPair(
            local_event_id=event.id,
            remote_event_id=created_remote_id,
            calendar_id=calendar_id,
            provider=provider.provider_name,
        )

    def delete_remote_event(
        self,
        provider: CalendarSyncProvider,
        *,
        calendar_id: str,
        remote_event_id: str,
    ) -> None:
        provider.delete_event(calendar_id, remote_event_id)

    def pull_events(
        self,
        provider: CalendarSyncProvider,
        *,
        calendar_id: str,
        cursor: SyncCursor | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> SyncResult:
        batch = provider.pull_changes(
            calendar_id,
            cursor=cursor,
            window_start=window_start,
            window_end=window_end,
        )

        created: list[SyncPair] = []
        updated: list[SyncPair] = []
        for remote_event in batch.events:
            pair, was_created = self._upsert_remote_event(
                provider=provider,
                calendar_id=calendar_id,
                remote_event=remote_event,
            )
            if was_created:
                created.append(pair)
            else:
                updated.append(pair)

        return SyncResult(
            created=tuple(created),
            updated=tuple(updated),
            deleted_remote_ids=batch.deleted_remote_ids,
            next_cursor=batch.next_cursor,
        )

    def _upsert_remote_event(
        self,
        *,
        provider: CalendarSyncProvider,
        calendar_id: str,
        remote_event: CalendarEvent,
    ) -> tuple[SyncPair, bool]:
        local_event = self._find_local_by_remote_reference(
            provider_name=provider.provider_name,
            calendar_id=calendar_id,
            remote_event_id=remote_event.id,
        )
        metadata = dict(remote_event.metadata)
        metadata["sync"] = {
            "provider": provider.provider_name,
            "calendar_id": calendar_id,
            "remote_event_id": remote_event.id,
        }

        if local_event is None:
            created = self.calendar_service.create_event(
                CalendarEventInput(
                    title=remote_event.title,
                    starts_at=remote_event.starts_at,
                    ends_at=remote_event.ends_at,
                    timezone=remote_event.timezone,
                    description=remote_event.description,
                    location=remote_event.location,
                    metadata=metadata,
                )
            )
            return (
                SyncPair(
                    local_event_id=created.id,
                    remote_event_id=remote_event.id,
                    calendar_id=calendar_id,
                    provider=provider.provider_name,
                ),
                True,
            )

        updated = replace(
            local_event,
            title=remote_event.title,
            starts_at=remote_event.starts_at,
            ends_at=remote_event.ends_at,
            timezone=remote_event.timezone,
            description=remote_event.description,
            location=remote_event.location,
            metadata=metadata,
        )
        self.calendar_service.repository.update(updated)
        return (
            SyncPair(
                local_event_id=updated.id,
                remote_event_id=remote_event.id,
                calendar_id=calendar_id,
                provider=provider.provider_name,
            ),
            False,
        )

    def _get_required_event(self, event_id: str) -> CalendarEvent:
        event = self.calendar_service.get_event(event_id)
        if event is None:
            raise KeyError(f"event {event_id} does not exist")
        return event

    def _find_local_by_remote_reference(
        self,
        *,
        provider_name: str,
        calendar_id: str,
        remote_event_id: str,
    ) -> CalendarEvent | None:
        for event in self.calendar_service.list_events():
            sync = event.metadata.get("sync")
            if not isinstance(sync, dict):
                continue
            if (
                sync.get("provider") == provider_name
                and sync.get("calendar_id") == calendar_id
                and sync.get("remote_event_id") == remote_event_id
            ):
                return event
        return None
