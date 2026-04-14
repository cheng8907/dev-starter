from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .models import Budget


class BudgetRepository(Protocol):
    def add(self, budget: Budget) -> Budget: ...

    def get(self, budget_id: str) -> Budget | None: ...

    def list(self) -> list[Budget]: ...

    def delete(self, budget_id: str) -> bool: ...


class InMemoryBudgetRepository:
    def __init__(self, budgets: Iterable[Budget] | None = None) -> None:
        self._budgets = {budget.id: budget for budget in budgets or ()}

    def add(self, budget: Budget) -> Budget:
        if budget.id in self._budgets:
            raise ValueError(f"budget {budget.id} already exists")
        self._budgets[budget.id] = budget
        return budget

    def get(self, budget_id: str) -> Budget | None:
        return self._budgets.get(budget_id)

    def list(self) -> list[Budget]:
        return sorted(self._budgets.values(), key=lambda budget: (budget.name.lower(), budget.id))

    def delete(self, budget_id: str) -> bool:
        return self._budgets.pop(budget_id, None) is not None
