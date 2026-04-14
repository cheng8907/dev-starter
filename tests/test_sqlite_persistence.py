from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from python.calendar_core import CalendarEventInput, CalendarService
from python.finance_core import (
    AccountInput,
    CategoryInput,
    FinanceService,
    TransactionInput,
    TransactionType,
)
from python.persistence import SqliteCalendarRepository, SqliteFinanceRepository


def dt(hour: int) -> datetime:
    return datetime(2026, 4, 14, hour, 0, tzinfo=UTC)


def test_sqlite_calendar_repository_persists_events(tmp_path: Path) -> None:
    repository = SqliteCalendarRepository(tmp_path / "app.sqlite3")
    service = CalendarService(repository)

    created = service.create_event(
        CalendarEventInput(
            title="Persisted event",
            starts_at=dt(9),
            ends_at=dt(10),
            metadata={"kind": "test"},
        )
    )

    reloaded_repository = SqliteCalendarRepository(tmp_path / "app.sqlite3")
    events = CalendarService(reloaded_repository).list_events()

    assert len(events) == 1
    assert events[0].id == created.id
    assert events[0].metadata["kind"] == "test"


def test_sqlite_finance_repository_persists_accounts_categories_and_transactions(tmp_path: Path) -> None:
    repository = SqliteFinanceRepository(tmp_path / "app.sqlite3")
    service = FinanceService(repository)
    account = service.create_account(AccountInput(name="Checking", type="bank", currency="USD"))
    category = service.create_category(CategoryInput(name="Bills", kind=TransactionType.EXPENSE))
    transaction = service.create_transaction(
        TransactionInput(
            type=TransactionType.EXPENSE,
            amount="88.40",
            currency="USD",
            occurred_at=dt(12),
            account_id=account.id,
            category_id=category.id,
            merchant="Utility Co",
            notes="Monthly payment",
        )
    )

    reloaded_repository = SqliteFinanceRepository(tmp_path / "app.sqlite3")
    reloaded_service = FinanceService(reloaded_repository)
    accounts = reloaded_service.list_accounts()
    categories = reloaded_service.list_categories()
    transactions = reloaded_service.list_transactions()

    assert len(accounts) == 1
    assert len(categories) == 1
    assert len(transactions) == 1
    assert transactions[0].id == transaction.id
    assert transactions[0].merchant == "Utility Co"
