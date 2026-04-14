from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from python.calendar_core import CalendarEventInput, CalendarService, InMemoryCalendarRepository
from python.finance_core import (
    AccountInput,
    CategoryInput,
    FinanceService,
    InMemoryFinanceRepository,
    TransactionInput,
    TransactionStatus,
    TransactionType,
    TransactionUpdate,
)


def dt(day: int, hour: int = 9) -> datetime:
    return datetime(2026, 4, day, hour, 0, tzinfo=UTC)


def build_service(*, with_calendar: bool = False) -> FinanceService:
    calendar_service = None
    if with_calendar:
        calendar_service = CalendarService(InMemoryCalendarRepository())
    return FinanceService(InMemoryFinanceRepository(), calendar_service=calendar_service)


def test_create_account_category_and_transaction() -> None:
    service = build_service()
    account = service.create_account(AccountInput(name="Main Checking", type="bank", currency="usd"))
    category = service.create_category(CategoryInput(name="Groceries", kind=TransactionType.EXPENSE))

    transaction = service.create_transaction(
        TransactionInput(
            type=TransactionType.EXPENSE,
            amount="18.5",
            currency="usd",
            occurred_at=dt(14),
            account_id=account.id,
            category_id=category.id,
            merchant="Trader Joe's",
            status=TransactionStatus.POSTED,
        )
    )

    assert transaction.amount == Decimal("18.50")
    assert transaction.currency == "USD"
    assert transaction.account_id == account.id
    assert transaction.category_id == category.id


def test_create_transaction_requires_existing_account() -> None:
    service = build_service()

    with pytest.raises(KeyError, match="account"):
        service.create_transaction(
            TransactionInput(
                type=TransactionType.EXPENSE,
                amount="20.00",
                currency="USD",
                occurred_at=dt(14),
                account_id="missing-account",
            )
        )


def test_create_transaction_from_calendar_event_links_event() -> None:
    calendar_service = CalendarService(InMemoryCalendarRepository())
    event = calendar_service.create_event(
        CalendarEventInput(
            title="Lunch meeting",
            starts_at=dt(15, 12),
            ends_at=dt(15, 13),
            description="Client lunch",
        )
    )
    service = FinanceService(InMemoryFinanceRepository(), calendar_service=calendar_service)
    account = service.create_account(AccountInput(name="Credit Card", type="credit_card", currency="USD"))
    category = service.create_category(CategoryInput(name="Dining", kind=TransactionType.EXPENSE))

    transaction = service.create_transaction_from_calendar_event(
        calendar_event_id=event.id,
        account_id=account.id,
        amount="42.00",
        currency="USD",
        category_id=category.id,
    )

    assert transaction.calendar_event_id == event.id
    assert transaction.merchant == "Lunch meeting"
    assert transaction.notes == "Client lunch"
    assert transaction.status == TransactionStatus.PLANNED


def test_update_transaction_changes_status_and_notes() -> None:
    service = build_service()
    account = service.create_account(AccountInput(name="Cash Wallet", type="cash", currency="USD"))
    transaction = service.create_transaction(
        TransactionInput(
            type=TransactionType.EXPENSE,
            amount="12.00",
            currency="USD",
            occurred_at=dt(16),
            account_id=account.id,
            status=TransactionStatus.PENDING,
        )
    )

    updated = service.update_transaction(
        transaction.id,
        TransactionUpdate(
            status=TransactionStatus.RECONCILED,
            notes="Confirmed by bank statement",
        ),
    )

    assert updated.status == TransactionStatus.RECONCILED
    assert updated.notes == "Confirmed by bank statement"


def test_summarize_by_category_and_account_balance() -> None:
    service = build_service()
    account = service.create_account(AccountInput(name="Checking", type="bank", currency="USD"))
    groceries = service.create_category(CategoryInput(name="Groceries", kind=TransactionType.EXPENSE))
    salary = service.create_category(CategoryInput(name="Salary", kind=TransactionType.INCOME))
    service.create_transaction(
        TransactionInput(
            type=TransactionType.EXPENSE,
            amount="30.00",
            currency="USD",
            occurred_at=dt(14),
            account_id=account.id,
            category_id=groceries.id,
        )
    )
    service.create_transaction(
        TransactionInput(
            type=TransactionType.INCOME,
            amount="1000.00",
            currency="USD",
            occurred_at=dt(15),
            account_id=account.id,
            category_id=salary.id,
        )
    )

    summary = service.summarize_by_category()
    balance = service.summarize_account_balance(account.id)

    assert summary["Groceries"] == Decimal("30.00")
    assert summary["Salary"] == Decimal("-1000.00")
    assert balance == Decimal("970.00")


def test_list_transactions_for_calendar_event_filters_results() -> None:
    calendar_service = CalendarService(InMemoryCalendarRepository())
    linked_event = calendar_service.create_event(
        CalendarEventInput(
            title="Commute",
            starts_at=dt(17, 8),
            ends_at=dt(17, 9),
        )
    )
    other_event = calendar_service.create_event(
        CalendarEventInput(
            title="Dinner",
            starts_at=dt(17, 19),
            ends_at=dt(17, 20),
        )
    )
    service = FinanceService(InMemoryFinanceRepository(), calendar_service=calendar_service)
    account = service.create_account(AccountInput(name="Transit Card", type="wallet", currency="USD"))

    first = service.create_transaction_from_calendar_event(
        calendar_event_id=linked_event.id,
        account_id=account.id,
        amount="3.20",
        currency="USD",
    )
    service.create_transaction_from_calendar_event(
        calendar_event_id=other_event.id,
        account_id=account.id,
        amount="24.00",
        currency="USD",
    )

    linked_transactions = service.list_transactions_for_calendar_event(linked_event.id)

    assert [transaction.id for transaction in linked_transactions] == [first.id]
