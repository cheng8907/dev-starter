from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime values must be timezone-aware")
    return value.astimezone(UTC)


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


class TransactionType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class TransactionStatus(StrEnum):
    PLANNED = "planned"
    PENDING = "pending"
    POSTED = "posted"
    RECONCILED = "reconciled"


@dataclass(slots=True, frozen=True)
class Account:
    id: str
    name: str
    type: str
    currency: str = "USD"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _ensure_nonempty(self.name, "name"))
        object.__setattr__(self, "type", _ensure_nonempty(self.type, "type"))
        object.__setattr__(self, "currency", _ensure_nonempty(self.currency, "currency").upper())


@dataclass(slots=True, frozen=True)
class AccountInput:
    name: str
    type: str
    currency: str = "USD"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_account(self, *, account_id: str | None = None) -> Account:
        return Account(
            id=account_id or str(uuid4()),
            name=self.name,
            type=self.type,
            currency=self.currency,
            metadata=dict(self.metadata),
        )


@dataclass(slots=True, frozen=True)
class Category:
    id: str
    name: str
    kind: TransactionType
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _ensure_nonempty(self.name, "name"))


@dataclass(slots=True, frozen=True)
class CategoryInput:
    name: str
    kind: TransactionType
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_category(self, *, category_id: str | None = None) -> Category:
        return Category(
            id=category_id or str(uuid4()),
            name=self.name,
            kind=self.kind,
            parent_id=self.parent_id,
            metadata=dict(self.metadata),
        )


@dataclass(slots=True, frozen=True)
class Transaction:
    id: str
    type: TransactionType
    amount: Decimal
    currency: str
    occurred_at: datetime
    account_id: str
    category_id: str | None = None
    posted_at: datetime | None = None
    merchant: str = ""
    notes: str = ""
    status: TransactionStatus = TransactionStatus.POSTED
    calendar_event_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _to_decimal(self.amount))
        object.__setattr__(self, "currency", _ensure_nonempty(self.currency, "currency").upper())
        object.__setattr__(self, "account_id", _ensure_nonempty(self.account_id, "account_id"))
        object.__setattr__(self, "occurred_at", _ensure_timezone(self.occurred_at))
        if self.posted_at is not None:
            object.__setattr__(self, "posted_at", _ensure_timezone(self.posted_at))
        object.__setattr__(self, "merchant", self.merchant.strip())
        object.__setattr__(self, "notes", self.notes.strip())
        if self.category_id is not None and not self.category_id.strip():
            raise ValueError("category_id cannot be blank when provided")
        if self.calendar_event_id is not None and not self.calendar_event_id.strip():
            raise ValueError("calendar_event_id cannot be blank when provided")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "amount": str(self.amount),
            "currency": self.currency,
            "occurred_at": self.occurred_at.isoformat(),
            "account_id": self.account_id,
            "category_id": self.category_id,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "merchant": self.merchant,
            "notes": self.notes,
            "status": self.status.value,
            "calendar_event_id": self.calendar_event_id,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True, frozen=True)
class TransactionInput:
    type: TransactionType
    amount: Decimal | int | float | str
    currency: str
    occurred_at: datetime
    account_id: str
    category_id: str | None = None
    posted_at: datetime | None = None
    merchant: str = ""
    notes: str = ""
    status: TransactionStatus = TransactionStatus.POSTED
    calendar_event_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_transaction(self, *, transaction_id: str | None = None) -> Transaction:
        return Transaction(
            id=transaction_id or str(uuid4()),
            type=self.type,
            amount=self.amount,
            currency=self.currency,
            occurred_at=self.occurred_at,
            account_id=self.account_id,
            category_id=self.category_id,
            posted_at=self.posted_at,
            merchant=self.merchant,
            notes=self.notes,
            status=self.status,
            calendar_event_id=self.calendar_event_id,
            metadata=dict(self.metadata),
        )


@dataclass(slots=True, frozen=True)
class TransactionUpdate:
    type: TransactionType | None = None
    amount: Decimal | int | float | str | None = None
    currency: str | None = None
    occurred_at: datetime | None = None
    account_id: str | None = None
    category_id: str | None = None
    posted_at: datetime | None = None
    merchant: str | None = None
    notes: str | None = None
    status: TransactionStatus | None = None
    calendar_event_id: str | None = None
    metadata: dict[str, Any] | None = None

    def apply_to(self, transaction: Transaction) -> Transaction:
        updates: dict[str, Any] = {}
        if self.type is not None:
            updates["type"] = self.type
        if self.amount is not None:
            updates["amount"] = self.amount
        if self.currency is not None:
            updates["currency"] = self.currency
        if self.occurred_at is not None:
            updates["occurred_at"] = self.occurred_at
        if self.account_id is not None:
            updates["account_id"] = self.account_id
        if self.category_id is not None:
            updates["category_id"] = self.category_id
        if self.posted_at is not None:
            updates["posted_at"] = self.posted_at
        if self.merchant is not None:
            updates["merchant"] = self.merchant
        if self.notes is not None:
            updates["notes"] = self.notes
        if self.status is not None:
            updates["status"] = self.status
        if self.calendar_event_id is not None:
            updates["calendar_event_id"] = self.calendar_event_id
        if self.metadata is not None:
            updates["metadata"] = dict(self.metadata)
        return replace(transaction, **updates)
