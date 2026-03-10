"""Database schema and indexes."""

from libs.database import Database


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0.0,
        color TEXT NOT NULL DEFAULT '#14B8A6',
        icon TEXT NOT NULL DEFAULT 'wallet',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        icon TEXT NOT NULL DEFAULT 'tag',
        color TEXT NOT NULL DEFAULT '#14B8A6',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
        amount REAL NOT NULL,
        category_id INTEGER,
        account_id INTEGER NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        date_created TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        currency TEXT NOT NULL DEFAULT '₽',
        theme TEXT NOT NULL DEFAULT 'light'
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date_created DESC, id DESC)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_type_date ON transactions(type, date_created DESC)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, date_created DESC)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_categories_type_name ON categories(type, name)",
]


def init_db(db: Database) -> None:
    with db.transaction():
        for statement in SCHEMA:
            db.execute(statement)
        for statement in INDEXES:
            db.execute(statement)
        db.execute(
            "INSERT OR IGNORE INTO settings (id, currency, theme) VALUES (1, '₽', 'light')"
        )
