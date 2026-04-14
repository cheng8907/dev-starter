from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from python.budget_core import BudgetInput, BudgetPeriod, BudgetService, InMemoryBudgetRepository
from python.finance_core import (
    AccountInput,
    CategoryInput,
    FinanceService,
    InMemoryFinanceRepository,
    TransactionInput,
    TransactionType,
)


def dt(day: int) -> datetime:
    return datetime(2026, 4, day, 9, 0, tzinfo=UTC)


def build_finance_service() -> FinanceService:
    return FinanceService(InMemoryFinanceRepository())


def test_budget_summary_uses_matching_category_and_currency() -> None:
    finance_service = build_finance_service()
    account = finance_service.create_account(AccountInput(name="Checking", type="bank", currency="USD"))
    groceries = finance_service.create_category(CategoryInput(name="Groceries", kind=TransactionType.EXPENSE))
    travel = finance_service.create_category(CategoryInput(name="Travel", kind=TransactionType.EXPENSE))
    finance_service.create_transaction(
        TransactionInput(
            type=TransactionType.EXPENSE,
            amount="35.00",
            currency="USD",
            occurred_at=dt(3),
            account_id=account.id,
            category_id=groceries.id,
        )
    )
    finance_service.create_transaction(
        TransactionInput(
            type=TransactionType.EXPENSE,
            amount="55.00",
            currency="USD",
            occurred_at=dt(5),
            account_id=account.id,
            category_id=travel.id,
        )
    )

    budget_service = BudgetService(InMemoryBudgetRepository(), finance_service)
    budget = budget_service.create_budget(
        BudgetInput(
            name="Groceries April",
            category_id=groceries.id,
            limit_amount="100.00",
            currency="USD",
            period=BudgetPeriod.MONTHLY,
        )
    )

    summary = budget_service.summarize_budget(budget.id, as_of=dt(10).date())

    assert summary.spent_amount == Decimal("35.00")
    assert summary.remaining_amount == Decimal("65.00")
    assert summary.is_over_budget is False


def test_budget_summary_detects_over_budget() -> None:
    finance_service = build_finance_service()
    account = finance_service.create_account(AccountInput(name="Card", type="credit_card", currency="USD"))
    dining = finance_service.create_category(CategoryInput(name="Dining", kind=TransactionType.EXPENSE))
    finance_service.create_transaction(
        TransactionInput(
            type=TransactionType.EXPENSE,
            amount="60.00",
            currency="USD",
            occurred_at=dt(7),
            account_id=account.id,
            category_id=dining.id,
        )
    )

    budget_service = BudgetService(InMemoryBudgetRepository(), finance_service)
    budget = budget_service.create_budget(
        BudgetInput(
            name="Dining Limit",
            category_id=dining.id,
            limit_amount="50.00",
        )
    )

    summary = budget_service.summarize_budget(budget.id, as_of=dt(10).date())

    assert summary.spent_amount == Decimal("60.00")
    assert summary.remaining_amount == Decimal("-10.00")
    assert summary.is_over_budget is True


def test_create_budget_requires_existing_category() -> None:
    finance_service = build_finance_service()
    budget_service = BudgetService(InMemoryBudgetRepository(), finance_service)

    with pytest.raises(KeyError, match="category"):
        budget_service.create_budget(
            BudgetInput(
                name="Bad Budget",
                category_id="missing-category",
                limit_amount="10.00",
            )
        )
