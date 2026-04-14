from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from python.calendar_core import CalendarEvent
from python.finance_core import Account, Category, Transaction, TransactionStatus, TransactionType


def initialize_sqlite_database(database_path: str | Path) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                timezone TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS finance_accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                currency TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS finance_categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                parent_id TEXT,
                metadata_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS finance_transactions (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                account_id TEXT NOT NULL,
                category_id TEXT,
                posted_at TEXT,
                merchant TEXT NOT NULL,
                notes TEXT NOT NULL,
                status TEXT NOT NULL,
                calendar_event_id TEXT,
                metadata_json TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES finance_accounts(id),
                FOREIGN KEY(category_id) REFERENCES finance_categories(id),
                FOREIGN KEY(calendar_event_id) REFERENCES calendar_events(id)
            )
            """
        )
        connection.commit()


def _to_metadata_json(metadata: dict[str, Any]) -> str:
    return json.dumps(metadata, sort_keys=True)


def _from_metadata_json(metadata_json: str) -> dict[str, Any]:
    value = json.loads(metadata_json)
    if not isinstance(value, dict):
        raise ValueError("metadata must deserialize to a dictionary")
    return value


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class _SqliteRepositoryBase:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        initialize_sqlite_database(self.database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


class SqliteCalendarRepository(_SqliteRepositoryBase):
    def add(self, event: CalendarEvent) -> CalendarEvent:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO calendar_events (
                        id, title, starts_at, ends_at, timezone, description, location, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.id,
                        event.title,
                        event.starts_at.isoformat(),
                        event.ends_at.isoformat(),
                        event.timezone,
                        event.description,
                        event.location,
                        _to_metadata_json(event.metadata),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"event {event.id} already exists") from exc
        return event

    def get(self, event_id: str) -> CalendarEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM calendar_events WHERE id = ?",
                (event_id,),
            ).fetchone()
        return self._row_to_event(row) if row else None

    def list(self) -> list[CalendarEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM calendar_events ORDER BY starts_at ASC, id ASC"
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def update(self, event: CalendarEvent) -> CalendarEvent:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE calendar_events
                SET title = ?, starts_at = ?, ends_at = ?, timezone = ?, description = ?, location = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    event.title,
                    event.starts_at.isoformat(),
                    event.ends_at.isoformat(),
                    event.timezone,
                    event.description,
                    event.location,
                    _to_metadata_json(event.metadata),
                    event.id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"event {event.id} does not exist")
        return event

    def delete(self, event_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        return cursor.rowcount > 0

    def _row_to_event(self, row: sqlite3.Row) -> CalendarEvent:
        return CalendarEvent(
            id=row["id"],
            title=row["title"],
            starts_at=_dt(row["starts_at"]),
            ends_at=_dt(row["ends_at"]),
            timezone=row["timezone"],
            description=row["description"],
            location=row["location"],
            metadata=_from_metadata_json(row["metadata_json"]),
        )


class SqliteFinanceRepository(_SqliteRepositoryBase):
    def add_account(self, account: Account) -> Account:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO finance_accounts (id, name, type, currency, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        account.id,
                        account.name,
                        account.type,
                        account.currency,
                        _to_metadata_json(account.metadata),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"account {account.id} already exists") from exc
        return account

    def get_account(self, account_id: str) -> Account | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM finance_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        return self._row_to_account(row) if row else None

    def list_accounts(self) -> list[Account]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM finance_accounts ORDER BY name ASC, id ASC"
            ).fetchall()
        return [self._row_to_account(row) for row in rows]

    def add_category(self, category: Category) -> Category:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO finance_categories (id, name, kind, parent_id, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        category.id,
                        category.name,
                        category.kind.value,
                        category.parent_id,
                        _to_metadata_json(category.metadata),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"category {category.id} already exists") from exc
        return category

    def get_category(self, category_id: str) -> Category | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM finance_categories WHERE id = ?",
                (category_id,),
            ).fetchone()
        return self._row_to_category(row) if row else None

    def list_categories(self) -> list[Category]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM finance_categories ORDER BY name ASC, id ASC"
            ).fetchall()
        return [self._row_to_category(row) for row in rows]

    def add_transaction(self, transaction: Transaction) -> Transaction:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO finance_transactions (
                        id, type, amount, currency, occurred_at, account_id, category_id, posted_at,
                        merchant, notes, status, calendar_event_id, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transaction.id,
                        transaction.type.value,
                        str(transaction.amount),
                        transaction.currency,
                        transaction.occurred_at.isoformat(),
                        transaction.account_id,
                        transaction.category_id,
                        transaction.posted_at.isoformat() if transaction.posted_at else None,
                        transaction.merchant,
                        transaction.notes,
                        transaction.status.value,
                        transaction.calendar_event_id,
                        _to_metadata_json(transaction.metadata),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"transaction {transaction.id} already exists") from exc
        return transaction

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM finance_transactions WHERE id = ?",
                (transaction_id,),
            ).fetchone()
        return self._row_to_transaction(row) if row else None

    def list_transactions(self) -> list[Transaction]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM finance_transactions ORDER BY occurred_at ASC, id ASC"
            ).fetchall()
        return [self._row_to_transaction(row) for row in rows]

    def update_transaction(self, transaction: Transaction) -> Transaction:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE finance_transactions
                SET type = ?, amount = ?, currency = ?, occurred_at = ?, account_id = ?, category_id = ?,
                    posted_at = ?, merchant = ?, notes = ?, status = ?, calendar_event_id = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    transaction.type.value,
                    str(transaction.amount),
                    transaction.currency,
                    transaction.occurred_at.isoformat(),
                    transaction.account_id,
                    transaction.category_id,
                    transaction.posted_at.isoformat() if transaction.posted_at else None,
                    transaction.merchant,
                    transaction.notes,
                    transaction.status.value,
                    transaction.calendar_event_id,
                    _to_metadata_json(transaction.metadata),
                    transaction.id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"transaction {transaction.id} does not exist")
        return transaction

    def delete_transaction(self, transaction_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM finance_transactions WHERE id = ?",
                (transaction_id,),
            )
        return cursor.rowcount > 0

    def _row_to_account(self, row: sqlite3.Row) -> Account:
        return Account(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            currency=row["currency"],
            metadata=_from_metadata_json(row["metadata_json"]),
        )

    def _row_to_category(self, row: sqlite3.Row) -> Category:
        return Category(
            id=row["id"],
            name=row["name"],
            kind=TransactionType(row["kind"]),
            parent_id=row["parent_id"],
            metadata=_from_metadata_json(row["metadata_json"]),
        )

    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        return Transaction(
            id=row["id"],
            type=TransactionType(row["type"]),
            amount=Decimal(row["amount"]),
            currency=row["currency"],
            occurred_at=_dt(row["occurred_at"]),
            account_id=row["account_id"],
            category_id=row["category_id"],
            posted_at=_dt(row["posted_at"]) if row["posted_at"] else None,
            merchant=row["merchant"],
            notes=row["notes"],
            status=TransactionStatus(row["status"]),
            calendar_event_id=row["calendar_event_id"],
            metadata=_from_metadata_json(row["metadata_json"]),
        )
