import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


class Database:
    """SQLite access layer optimized for mobile reads.

    Key goals:
    - one long-lived connection
    - WAL mode for smoother read/write behavior
    - no commit on SELECTs
    - coarse cache invalidation by revision counter
    - aggregate queries in SQL to avoid N+1 on UI screens
    """

    def __init__(self, db_name: str = "finwise.db"):
        self.db_name = str(Path(db_name))
        self.conn: Optional[sqlite3.Connection] = None
        self._revision = 0
        self._cache: Dict[Tuple[Any, ...], Tuple[int, Any]] = {}
        self.connect()

    def connect(self) -> None:
        self.conn = sqlite3.connect(
            self.db_name,
            check_same_thread=False,
            timeout=15,
            isolation_level=None,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA temp_store = MEMORY")
        self.conn.execute("PRAGMA cache_size = -20000")
        self.conn.execute("PRAGMA busy_timeout = 15000")

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    @property
    def revision(self) -> int:
        return self._revision

    def invalidate(self) -> None:
        self._revision += 1
        self._cache.clear()

    @contextmanager
    def transaction(self):
        assert self.conn is not None
        try:
            self.conn.execute("BEGIN")
            yield
            self.conn.execute("COMMIT")
            self.invalidate()
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def execute(self, query: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        assert self.conn is not None
        return self.conn.execute(query, params)

    def executemany(self, query: str, items: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        assert self.conn is not None
        return self.conn.executemany(query, items)

    def fetchall(self, query: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        return list(self.execute(query, params).fetchall())

    def fetchone(self, query: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        return self.execute(query, params).fetchone()

    def _cached(self, key: Tuple[Any, ...], loader):
        cached = self._cache.get(key)
        if cached and cached[0] == self._revision:
            return cached[1]
        value = loader()
        self._cache[key] = (self._revision, value)
        return value

    def _normalize_date(self, value: Optional[str]) -> str:
        if not value:
            return datetime.now().strftime("%Y-%m-%d")
        value = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y-%m-%d")

    def format_display_date(self, value: Optional[str]) -> str:
        if not value:
            return ""
        value = str(value).split(" ")[0]
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).strftime("%d-%m-%Y")
            except ValueError:
                continue
        return value

    # settings
    def is_first_run(self) -> bool:
        row = self.fetchone("SELECT COUNT(*) AS count FROM accounts")
        return not row or int(row["count"]) == 0

    def get_currency(self) -> str:
        row = self.fetchone("SELECT currency FROM settings WHERE id = 1")
        return row["currency"] if row else "₽"

    def set_currency(self, currency: str) -> None:
        with self.transaction():
            self.execute("UPDATE settings SET currency = ? WHERE id = 1", (currency,))

    def get_theme(self) -> str:
        row = self.fetchone("SELECT theme FROM settings WHERE id = 1")
        return row["theme"] if row else "light"

    def set_theme(self, theme: str) -> None:
        with self.transaction():
            self.execute("UPDATE settings SET theme = ? WHERE id = 1", (theme,))

    # accounts
    def get_accounts(self) -> List[sqlite3.Row]:
        return self._cached(
            ("accounts",),
            lambda: self.fetchall(
                "SELECT id, name, type, balance, color, icon, created_at "
                "FROM accounts ORDER BY created_at, id"
            ),
        )

    def get_account(self, account_id: int) -> Optional[sqlite3.Row]:
        return self.fetchone(
            "SELECT id, name, type, balance, color, icon, created_at FROM accounts WHERE id = ?",
            (account_id,),
        )

    def create_account(
        self,
        name: str,
        acc_type: str = "cash",
        balance: float = 0.0,
        color: str = "#14B8A6",
        icon: str = "wallet",
    ) -> int:
        with self.transaction():
            cur = self.execute(
                "INSERT INTO accounts (name, type, balance, color, icon) VALUES (?, ?, ?, ?, ?)",
                (name, acc_type, float(balance), color, icon),
            )
        return int(cur.lastrowid)

    def update_account(self, account_id: int, name: str, balance: float) -> None:
        with self.transaction():
            self.execute(
                "UPDATE accounts SET name = ?, balance = ? WHERE id = ?",
                (name, float(balance), account_id),
            )

    def update_account_balance(self, account_id: int, delta: float) -> None:
        self.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (float(delta), account_id))

    def delete_account(self, account_id: int) -> None:
        with self.transaction():
            self.execute("DELETE FROM transactions WHERE account_id = ?", (account_id,))
            self.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    def get_total_balance(self) -> float:
        return self._cached(
            ("total_balance",),
            lambda: float(
                (self.fetchone("SELECT COALESCE(SUM(balance), 0) AS total FROM accounts") or {"total": 0})[
                    "total"
                ]
                or 0
            ),
        )

    def get_accounts_with_stats(self) -> List[sqlite3.Row]:
        return self._cached(
            ("accounts_with_stats",),
            lambda: self.fetchall(
                """
                SELECT
                    a.id,
                    a.name,
                    a.type,
                    a.balance,
                    a.color,
                    a.icon,
                    a.created_at,
                    COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) AS income,
                    COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS expense,
                    COUNT(t.id) AS operations_count
                FROM accounts a
                LEFT JOIN transactions t ON t.account_id = a.id
                GROUP BY a.id
                ORDER BY a.created_at, a.id
                """
            ),
        )

    # categories
    def create_category(self, name: str, category_type: str, icon: str = "tag", color: str = "#14B8A6") -> int:
        with self.transaction():
            cur = self.execute(
                "INSERT INTO categories (name, type, icon, color) VALUES (?, ?, ?, ?)",
                (name, category_type, icon, color),
            )
        return int(cur.lastrowid)

    def get_categories(self, category_type: Optional[str] = None) -> List[sqlite3.Row]:
        key = ("categories", category_type or "all")
        if category_type:
            return self._cached(
                key,
                lambda: self.fetchall(
                    "SELECT id, name, type, icon, color, created_at FROM categories WHERE type = ? ORDER BY name, id",
                    (category_type,),
                ),
            )
        return self._cached(
            key,
            lambda: self.fetchall("SELECT id, name, type, icon, color, created_at FROM categories ORDER BY type, name, id"),
        )

    # transactions
    def create_transaction(
        self,
        trans_type: str,
        amount: float,
        category_id: Optional[int],
        account_id: int,
        note: str = "",
        date: Optional[str] = None,
    ) -> int:
        norm_date = self._normalize_date(date)
        with self.transaction():
            cur = self.execute(
                """
                INSERT INTO transactions (type, amount, category_id, account_id, note, date_created)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (trans_type, float(amount), category_id, account_id, note.strip(), norm_date),
            )
            delta = float(amount) if trans_type == "income" else -float(amount)
            self.update_account_balance(account_id, delta)
        return int(cur.lastrowid)

    def get_transaction(self, trans_id: int) -> Optional[sqlite3.Row]:
        return self.fetchone(
            """
            SELECT
                t.*,
                c.name AS category_name,
                c.icon AS category_icon,
                c.color AS category_color,
                a.name AS account_name
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            LEFT JOIN accounts a ON a.id = t.account_id
            WHERE t.id = ?
            """,
            (trans_id,),
        )

    def update_transaction(
        self,
        trans_id: int,
        trans_type: str,
        amount: float,
        category_id: Optional[int],
        account_id: int,
        note: str,
        date: Optional[str],
    ) -> None:
        old = self.get_transaction(trans_id)
        if old is None:
            return
        norm_date = self._normalize_date(date)
        with self.transaction():
            old_delta = -float(old["amount"]) if old["type"] == "income" else float(old["amount"])
            self.update_account_balance(int(old["account_id"]), old_delta)
            self.execute(
                """
                UPDATE transactions
                SET type = ?, amount = ?, category_id = ?, account_id = ?, note = ?, date_created = ?
                WHERE id = ?
                """,
                (trans_type, float(amount), category_id, account_id, note.strip(), norm_date, trans_id),
            )
            new_delta = float(amount) if trans_type == "income" else -float(amount)
            self.update_account_balance(account_id, new_delta)

    def delete_transaction(self, trans_id: int) -> None:
        old = self.get_transaction(trans_id)
        if old is None:
            return
        with self.transaction():
            reverse = -float(old["amount"]) if old["type"] == "income" else float(old["amount"])
            self.update_account_balance(int(old["account_id"]), reverse)
            self.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))

    def get_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[sqlite3.Row]:
        filters = filters or {}
        conditions: List[str] = []
        params: List[Any] = []

        if filters.get("type") and filters["type"] != "all":
            conditions.append("t.type = ?")
            params.append(filters["type"])
        if filters.get("account_id"):
            conditions.append("t.account_id = ?")
            params.append(filters["account_id"])
        if filters.get("category_id"):
            conditions.append("t.category_id = ?")
            params.append(filters["category_id"])
        if filters.get("date_from"):
            conditions.append("t.date_created >= ?")
            params.append(self._normalize_date(filters["date_from"]))
        if filters.get("date_to"):
            conditions.append("t.date_created <= ?")
            params.append(self._normalize_date(filters["date_to"]))
        if filters.get("search"):
            conditions.append("(LOWER(t.note) LIKE ? OR LOWER(COALESCE(c.name, '')) LIKE ?)")
            q = f"%{str(filters['search']).strip().lower()}%"
            params.extend([q, q])

        query = (
            "SELECT t.id, t.type, t.amount, t.category_id, t.account_id, t.note, t.date_created, "
            "c.name AS category_name, c.icon AS category_icon, c.color AS category_color, "
            "a.name AS account_name "
            "FROM transactions t "
            "LEFT JOIN categories c ON c.id = t.category_id "
            "LEFT JOIN accounts a ON a.id = t.account_id"
        )
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.date_created DESC, t.id DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        return self.fetchall(query, tuple(params))

    def get_recent_transactions(self, limit: int = 4) -> List[sqlite3.Row]:
        return self.get_transactions(limit=limit)

    def get_monthly_summary(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, float]:
        now = datetime.now()
        year = int(year or now.year)
        month = int(month or now.month)
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1:04d}-01-01"
        else:
            end_date = f"{year:04d}-{month + 1:02d}-01"

        key = ("monthly_summary", year, month)

        def loader() -> Dict[str, float]:
            row = self.fetchone(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expenses,
                    COUNT(*) AS count
                FROM transactions
                WHERE date_created >= ? AND date_created < ?
                """,
                (start_date, end_date),
            )
            return {
                "income": float(row["income"] or 0),
                "expenses": float(row["expenses"] or 0),
                "count": int(row["count"] or 0),
            }

        return self._cached(key, loader)

    def get_analytics_snapshot(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        now = datetime.now()
        year = int(year or now.year)
        month = int(month or now.month)
        key = ("analytics_snapshot", year, month)

        def loader() -> Dict[str, Any]:
            summary = self.get_monthly_summary(year, month)
            start_date = f"{year:04d}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1:04d}-01-01"
            else:
                end_date = f"{year:04d}-{month + 1:02d}-01"

            breakdown = self.fetchall(
                """
                SELECT
                    t.type,
                    COALESCE(c.name, 'Без категории') AS category_name,
                    COALESCE(c.icon, 'tag') AS category_icon,
                    COALESCE(c.color, '#14B8A6') AS category_color,
                    SUM(t.amount) AS total,
                    COUNT(t.id) AS items_count
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE t.date_created >= ? AND t.date_created < ?
                GROUP BY t.type, COALESCE(c.name, 'Без категории'), COALESCE(c.icon, 'tag'), COALESCE(c.color, '#14B8A6')
                ORDER BY total DESC, category_name ASC
                """,
                (start_date, end_date),
            )

            month_rows = self.fetchall(
                """
                WITH RECURSIVE months(idx, month_start) AS (
                    SELECT 0, date('now', 'start of month', '-5 months')
                    UNION ALL
                    SELECT idx + 1, date(month_start, '+1 month')
                    FROM months
                    WHERE idx < 5
                )
                SELECT
                    strftime('%Y-%m', m.month_start) AS month_key,
                    COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) AS income,
                    COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS expense
                FROM months m
                LEFT JOIN transactions t
                    ON t.date_created >= m.month_start
                   AND t.date_created < date(m.month_start, '+1 month')
                GROUP BY month_key
                ORDER BY month_key
                """
            )

            expenses_total = float(summary["expenses"])
            income_total = float(summary["income"])
            expense_items: List[Dict[str, Any]] = []
            income_items: List[Dict[str, Any]] = []
            for row in breakdown:
                item = {
                    "type": row["type"],
                    "category_name": row["category_name"],
                    "category_icon": row["category_icon"],
                    "category_color": row["category_color"],
                    "total": float(row["total"] or 0),
                    "items_count": int(row["items_count"] or 0),
                }
                if item["type"] == "expense":
                    item["share"] = (item["total"] / expenses_total) if expenses_total > 0 else 0.0
                    expense_items.append(item)
                else:
                    item["share"] = (item["total"] / income_total) if income_total > 0 else 0.0
                    income_items.append(item)

            trend = []
            for row in month_rows:
                trend.append(
                    {
                        "month": row["month_key"],
                        "income": float(row["income"] or 0),
                        "expense": float(row["expense"] or 0),
                    }
                )

            return {
                "summary": summary,
                "expense_breakdown": expense_items,
                "income_breakdown": income_items,
                "trend": trend,
            }

        return self._cached(key, loader)

    def populate_demo_data(self) -> None:
        with self.transaction():
            if self.fetchone("SELECT COUNT(*) AS count FROM categories")["count"] == 0:
                categories = [
                    ("Еда", "expense", "food", "#F59E0B"),
                    ("Транспорт", "expense", "train-car", "#3B82F6"),
                    ("Подписки", "expense", "television-play", "#8B5CF6"),
                    ("Покупки", "expense", "cart", "#EC4899"),
                    ("Здоровье", "expense", "heart-pulse", "#EF4444"),
                    ("Дом", "expense", "home", "#14B8A6"),
                    ("Развлечения", "expense", "movie-open", "#F97316"),
                    ("Зарплата", "income", "cash-check", "#10B981"),
                    ("Фриланс", "income", "laptop", "#06B6D4"),
                    ("Подарок", "income", "gift", "#A855F7"),
                ]
                self.executemany(
                    "INSERT INTO categories (name, type, icon, color) VALUES (?, ?, ?, ?)",
                    categories,
                )

            if self.fetchone("SELECT COUNT(*) AS count FROM accounts")["count"] == 0:
                accounts = [
                    ("Наличные", "cash", 12000.0, "#14B8A6", "wallet"),
                    ("Основная карта", "card", 48600.0, "#3B82F6", "credit-card"),
                    ("Сбережения", "savings", 160000.0, "#10B981", "piggy-bank"),
                ]
                self.executemany(
                    "INSERT INTO accounts (name, type, balance, color, icon) VALUES (?, ?, ?, ?, ?)",
                    accounts,
                )

            if self.fetchone("SELECT COUNT(*) AS count FROM transactions")["count"] == 0:
                account_rows = self.fetchall("SELECT id, name FROM accounts ORDER BY id")
                category_rows = self.fetchall("SELECT id, name, type FROM categories ORDER BY id")
                account_map = {row["name"]: int(row["id"]) for row in account_rows}
                category_map = {(row["name"], row["type"]): int(row["id"]) for row in category_rows}
                today = datetime.now().date()
                items = []
                for index, payload in enumerate(
                    [
                        ("income", 95000, "Зарплата", "Основная карта", "Зарплата за месяц", 1),
                        ("expense", 4200, "Еда", "Основная карта", "Продукты на неделю", 2),
                        ("expense", 980, "Транспорт", "Основная карта", "Такси", 3),
                        ("expense", 799, "Подписки", "Основная карта", "Музыкальный сервис", 5),
                        ("income", 17500, "Фриланс", "Основная карта", "Лендинг для клиента", 8),
                        ("expense", 2300, "Развлечения", "Наличные", "Кино и кофе", 9),
                        ("expense", 6900, "Покупки", "Основная карта", "Одежда", 12),
                        ("expense", 1850, "Дом", "Наличные", "Хозтовары", 15),
                        ("income", 5000, "Подарок", "Наличные", "Подарок на праздник", 19),
                        ("expense", 3100, "Здоровье", "Основная карта", "Аптека", 22),
                    ]
                ):
                    trans_type, amount, cat_name, acc_name, note, delta_days = payload
                    date_value = (today - timedelta(days=delta_days)).strftime("%Y-%m-%d")
                    items.append(
                        (
                            trans_type,
                            float(amount),
                            category_map[(cat_name, trans_type)],
                            account_map[acc_name],
                            note,
                            date_value,
                        )
                    )
                self.executemany(
                    """
                    INSERT INTO transactions (type, amount, category_id, account_id, note, date_created)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    items,
                )
                self.execute(
                    """
                    UPDATE accounts
                    SET balance = (
                        SELECT COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE -t.amount END), 0)
                        FROM transactions t
                        WHERE t.account_id = accounts.id
                    )
                    """
                )
