from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from python.calendar_core import CalendarService

from .models import (
    Account,
    AccountInput,
    Category,
    CategoryInput,
    Transaction,
    TransactionInput,
    TransactionStatus,
    TransactionType,
    TransactionUpdate,
)
from .storage import FinanceRepository


class FinanceService:
    def __init__(
        self,
        repository: FinanceRepository,
        *,
        calendar_service: CalendarService | None = None,
    ) -> None:
        self.repository = repository
        self.calendar_service = calendar_service

    def create_account(self, account_input: AccountInput) -> Account:
        return self.repository.add_account(account_input.to_account())

    def get_account(self, account_id: str) -> Account | None:
        return self.repository.get_account(account_id)

    def list_accounts(self) -> list[Account]:
        return self.repository.list_accounts()

    def create_category(self, category_input: CategoryInput) -> Category:
        if category_input.parent_id is not None and self.repository.get_category(category_input.parent_id) is None:
            raise KeyError(f"category {category_input.parent_id} does not exist")
        return self.repository.add_category(category_input.to_category())

    def get_category(self, category_id: str) -> Category | None:
        return self.repository.get_category(category_id)

    def list_categories(self) -> list[Category]:
        return self.repository.list_categories()

    def create_transaction(self, transaction_input: TransactionInput) -> Transaction:
        self._validate_references(transaction_input.account_id, transaction_input.category_id)
        self._validate_calendar_link(transaction_input.calendar_event_id)
        return self.repository.add_transaction(transaction_input.to_transaction())

    def create_transaction_from_calendar_event(
        self,
        *,
        calendar_event_id: str,
        account_id: str,
        amount: Decimal | int | float | str,
        currency: str,
        category_id: str | None = None,
        merchant: str = "",
        notes: str = "",
    ) -> Transaction:
        if self.calendar_service is None:
            raise ValueError("calendar_service is required to create transactions from calendar events")
        event = self.calendar_service.get_event(calendar_event_id)
        if event is None:
            raise KeyError(f"calendar event {calendar_event_id} does not exist")
        return self.create_transaction(
            TransactionInput(
                type=TransactionType.EXPENSE,
                amount=amount,
                currency=currency,
                occurred_at=event.starts_at,
                account_id=account_id,
                category_id=category_id,
                merchant=merchant or event.title,
                notes=notes or event.description,
                calendar_event_id=calendar_event_id,
                status=TransactionStatus.PLANNED,
                metadata={"source": "calendar"},
            )
        )

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        return self.repository.get_transaction(transaction_id)

    def list_transactions(self) -> list[Transaction]:
        return self.repository.list_transactions()

    def list_transactions_for_calendar_event(self, calendar_event_id: str) -> list[Transaction]:
        return [
            transaction
            for transaction in self.repository.list_transactions()
            if transaction.calendar_event_id == calendar_event_id
        ]

    def list_transactions_in_range(
        self,
        range_start: datetime,
        range_end: datetime,
    ) -> list[Transaction]:
        if range_end <= range_start:
            raise ValueError("range_end must be later than range_start")
        return [
            transaction
            for transaction in self.repository.list_transactions()
            if range_start <= transaction.occurred_at < range_end
        ]

    def update_transaction(self, transaction_id: str, transaction_update: TransactionUpdate) -> Transaction:
        existing = self._get_required_transaction(transaction_id)
        updated = transaction_update.apply_to(existing)
        self._validate_references(updated.account_id, updated.category_id)
        self._validate_calendar_link(updated.calendar_event_id)
        return self.repository.update_transaction(updated)

    def delete_transaction(self, transaction_id: str) -> bool:
        return self.repository.delete_transaction(transaction_id)

    def summarize_by_category(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for transaction in self.repository.list_transactions():
            category_name = "Uncategorized"
            if transaction.category_id is not None:
                category = self.repository.get_category(transaction.category_id)
                if category is not None:
                    category_name = category.name

            signed_amount = transaction.amount
            if transaction.type == TransactionType.INCOME:
                signed_amount = -transaction.amount
            totals[category_name] = totals.get(category_name, Decimal("0.00")) + signed_amount
        return totals

    def summarize_account_balance(self, account_id: str) -> Decimal:
        if self.repository.get_account(account_id) is None:
            raise KeyError(f"account {account_id} does not exist")
        balance = Decimal("0.00")
        for transaction in self.repository.list_transactions():
            if transaction.account_id != account_id:
                continue
            if transaction.type == TransactionType.INCOME:
                balance += transaction.amount
            else:
                balance -= transaction.amount
        return balance

    def _validate_references(self, account_id: str, category_id: str | None) -> None:
        if self.repository.get_account(account_id) is None:
            raise KeyError(f"account {account_id} does not exist")
        if category_id is not None and self.repository.get_category(category_id) is None:
            raise KeyError(f"category {category_id} does not exist")

    def _validate_calendar_link(self, calendar_event_id: str | None) -> None:
        if calendar_event_id is None:
            return
        if self.calendar_service is None:
            raise ValueError("calendar_service is required for calendar-linked transactions")
        if self.calendar_service.get_event(calendar_event_id) is None:
            raise KeyError(f"calendar event {calendar_event_id} does not exist")

    def _get_required_transaction(self, transaction_id: str) -> Transaction:
        transaction = self.repository.get_transaction(transaction_id)
        if transaction is None:
            raise KeyError(f"transaction {transaction_id} does not exist")
        return transaction
