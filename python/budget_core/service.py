from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from python.finance_core import FinanceService, TransactionType

from .models import Budget, BudgetInput, BudgetPeriod, BudgetSummary
from .storage import BudgetRepository


class BudgetService:
    def __init__(self, repository: BudgetRepository, finance_service: FinanceService) -> None:
        self.repository = repository
        self.finance_service = finance_service

    def create_budget(self, budget_input: BudgetInput) -> Budget:
        if self.finance_service.get_category(budget_input.category_id) is None:
            raise KeyError(f"category {budget_input.category_id} does not exist")
        return self.repository.add(budget_input.to_budget())

    def get_budget(self, budget_id: str) -> Budget | None:
        return self.repository.get(budget_id)

    def list_budgets(self) -> list[Budget]:
        return self.repository.list()

    def delete_budget(self, budget_id: str) -> bool:
        return self.repository.delete(budget_id)

    def summarize_budget(self, budget_id: str, *, as_of: date | None = None) -> BudgetSummary:
        budget = self._get_required_budget(budget_id)
        anchor = as_of or date.today()
        period_start, period_end = self._period_bounds(budget, anchor)
        range_start = datetime.combine(period_start, time.min, tzinfo=UTC)
        range_end = datetime.combine(period_end, time.min, tzinfo=UTC)

        spent = Decimal("0.00")
        for transaction in self.finance_service.list_transactions_in_range(range_start, range_end):
            if transaction.category_id != budget.category_id:
                continue
            if transaction.currency != budget.currency:
                continue
            if transaction.type == TransactionType.EXPENSE:
                spent += transaction.amount
            elif transaction.type == TransactionType.INCOME:
                spent -= transaction.amount

        remaining = budget.limit_amount - spent
        utilization = (spent / budget.limit_amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return BudgetSummary(
            budget_id=budget.id,
            budget_name=budget.name,
            category_id=budget.category_id,
            period_start=period_start,
            period_end=period_end,
            limit_amount=budget.limit_amount,
            spent_amount=spent.quantize(Decimal("0.01")),
            remaining_amount=remaining.quantize(Decimal("0.01")),
            utilization_ratio=utilization,
            is_over_budget=spent > budget.limit_amount,
        )

    def summarize_all_budgets(self, *, as_of: date | None = None) -> list[BudgetSummary]:
        return [self.summarize_budget(budget.id, as_of=as_of) for budget in self.repository.list()]

    def _period_bounds(self, budget: Budget, anchor: date) -> tuple[date, date]:
        if budget.period == BudgetPeriod.MONTHLY:
            first = date(anchor.year, anchor.month, 1)
            _, days_in_month = monthrange(anchor.year, anchor.month)
            next_boundary = date(anchor.year, anchor.month, days_in_month).replace(day=days_in_month)
            return first, next_boundary.replace(day=days_in_month).fromordinal(next_boundary.toordinal() + 1)
        if budget.period == BudgetPeriod.YEARLY:
            first = date(anchor.year, 1, 1)
            return first, date(anchor.year + 1, 1, 1)
        raise ValueError(f"unsupported budget period {budget.period}")

    def _get_required_budget(self, budget_id: str) -> Budget:
        budget = self.repository.get(budget_id)
        if budget is None:
            raise KeyError(f"budget {budget_id} does not exist")
        return budget
