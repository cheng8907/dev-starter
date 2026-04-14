from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .models import Account, Category, Transaction


class FinanceRepository(Protocol):
    def add_account(self, account: Account) -> Account: ...

    def get_account(self, account_id: str) -> Account | None: ...

    def list_accounts(self) -> list[Account]: ...

    def add_category(self, category: Category) -> Category: ...

    def get_category(self, category_id: str) -> Category | None: ...

    def list_categories(self) -> list[Category]: ...

    def add_transaction(self, transaction: Transaction) -> Transaction: ...

    def get_transaction(self, transaction_id: str) -> Transaction | None: ...

    def list_transactions(self) -> list[Transaction]: ...

    def update_transaction(self, transaction: Transaction) -> Transaction: ...

    def delete_transaction(self, transaction_id: str) -> bool: ...


class InMemoryFinanceRepository:
    def __init__(
        self,
        *,
        accounts: Iterable[Account] | None = None,
        categories: Iterable[Category] | None = None,
        transactions: Iterable[Transaction] | None = None,
    ) -> None:
        self._accounts = {account.id: account for account in accounts or ()}
        self._categories = {category.id: category for category in categories or ()}
        self._transactions = {transaction.id: transaction for transaction in transactions or ()}

    def add_account(self, account: Account) -> Account:
        if account.id in self._accounts:
            raise ValueError(f"account {account.id} already exists")
        self._accounts[account.id] = account
        return account

    def get_account(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    def list_accounts(self) -> list[Account]:
        return sorted(self._accounts.values(), key=lambda account: (account.name.lower(), account.id))

    def add_category(self, category: Category) -> Category:
        if category.id in self._categories:
            raise ValueError(f"category {category.id} already exists")
        self._categories[category.id] = category
        return category

    def get_category(self, category_id: str) -> Category | None:
        return self._categories.get(category_id)

    def list_categories(self) -> list[Category]:
        return sorted(self._categories.values(), key=lambda category: (category.name.lower(), category.id))

    def add_transaction(self, transaction: Transaction) -> Transaction:
        if transaction.id in self._transactions:
            raise ValueError(f"transaction {transaction.id} already exists")
        self._transactions[transaction.id] = transaction
        return transaction

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        return self._transactions.get(transaction_id)

    def list_transactions(self) -> list[Transaction]:
        return sorted(
            self._transactions.values(),
            key=lambda transaction: (transaction.occurred_at, transaction.id),
        )

    def update_transaction(self, transaction: Transaction) -> Transaction:
        if transaction.id not in self._transactions:
            raise KeyError(f"transaction {transaction.id} does not exist")
        self._transactions[transaction.id] = transaction
        return transaction

    def delete_transaction(self, transaction_id: str) -> bool:
        return self._transactions.pop(transaction_id, None) is not None
