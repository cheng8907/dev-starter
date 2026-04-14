from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _ensure_nonempty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


def _to_decimal(value: Decimal | int | float | str) -> Decimal:
    amount = Decimal(str(value))
    if amount <= Decimal("0"):
        raise ValueError("amount must be greater than zero")
    return amount.quantize(Decimal("0.01"))


class BudgetPeriod(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass(slots=True, frozen=True)
class Budget:
    id: str
    name: str
    category_id: str
    limit_amount: Decimal
    currency: str = "USD"
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    starts_on: date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _ensure_nonempty(self.name, "name"))
        object.__setattr__(self, "category_id", _ensure_nonempty(self.category_id, "category_id"))
        object.__setattr__(self, "limit_amount", _to_decimal(self.limit_amount))
        object.__setattr__(self, "currency", _ensure_nonempty(self.currency, "currency").upper())


@dataclass(slots=True, frozen=True)
class BudgetInput:
    name: str
    category_id: str
    limit_amount: Decimal | int | float | str
    currency: str = "USD"
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    starts_on: date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_budget(self, *, budget_id: str | None = None) -> Budget:
        return Budget(
            id=budget_id or str(uuid4()),
            name=self.name,
            category_id=self.category_id,
            limit_amount=self.limit_amount,
            currency=self.currency,
            period=self.period,
            starts_on=self.starts_on,
            metadata=dict(self.metadata),
        )


@dataclass(slots=True, frozen=True)
class BudgetSummary:
    budget_id: str
    budget_name: str
    category_id: str
    period_start: date
    period_end: date
    limit_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    utilization_ratio: Decimal
    is_over_budget: bool
