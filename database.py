"""
database.py
------------
Handles all SQLite database logic for the Restaurant Management app.

Kept completely separate from the UI (ui.py) so that:
- the data layer can be unit-tested without opening any tkinter window
- the storage backend could be swapped later without touching the UI code
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

# Directory this file lives in — used so restaurant.db is always created
# next to the source code, regardless of the folder Python was launched from.
_PROJECT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Simple data classes (make query results easier to work with than raw tuples)
# ---------------------------------------------------------------------------
@dataclass
class Customer:
    id: int
    name: str
    phone_number: str | None = None


@dataclass
class MenuItem:
    id: int
    name: str
    price: float
    category: str = "Food"  # "Food" or "Drink"


@dataclass
class Order:
    id: int
    customer_name: str
    menu_item_name: str
    price: float
    quantity: int
    reservation_id: int | None = None
    created_at: str | None = None

    @property
    def total(self) -> float:
        return self.price * self.quantity


@dataclass
class Table:
    id: int
    number: int
    capacity: int


@dataclass
class Reservation:
    id: int
    table_number: int
    table_capacity: int
    customer_name: str
    date: str
    time: str
    guests: int


# A customer is considered a "Regular" once they've placed at least this
# many separate orders. Tweak this single constant to change the threshold
# used everywhere (analysis table, headline stats, CSV export).
REGULAR_CUSTOMER_ORDER_THRESHOLD = 5


@dataclass
class CustomerSpending:
    """One row of the customer analysis: aggregated across every order ever placed by this phone number."""
    phone_number: str
    name: str
    order_count: int
    items_count: int
    total_spent: float

    @property
    def segment(self) -> str:
        return "Regular" if self.order_count >= REGULAR_CUSTOMER_ORDER_THRESHOLD else "Occasional"


@dataclass
class ItemSales:
    """One row of the best-seller analysis for a menu item (food or drink)."""
    name: str
    category: str
    quantity_sold: int
    revenue: float


# ---------------------------------------------------------------------------
# Database wrapper
# ---------------------------------------------------------------------------
class Database:
    """
    Wraps a SQLite connection and exposes CRUD operations.

    Use Database("restaurant.db") for normal use, or Database(":memory:")
    in tests so each test run starts from a clean, disposable database.
    """

    def __init__(self, db_path: str = "restaurant.db"):
        # :memory: (used by the tests) is left untouched. Otherwise, resolve
        # relative paths against this file's directory instead of the
        # current working directory, so it doesn't matter where the app
        # was launched from (double-click, IDE "Run" button, terminal, ...).
        if db_path != ":memory:" and not Path(db_path).is_absolute():
            db_path = str(_PROJECT_DIR / db_path)

        self.db_path = db_path

        if db_path != ":memory:":
            self._diagnose_path_before_connecting(db_path)

        try:
            self.conn = sqlite3.connect(db_path)
        except sqlite3.OperationalError as e:
            raise sqlite3.OperationalError(
                f"Could not open database file at '{db_path}'.\n"
                "Check that the folder exists and that you have write "
                "permission there (this can happen with OneDrive-synced "
                "folders or restricted directories)."
            ) from e

        # Needed so that ON DELETE CASCADE below actually takes effect
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    @staticmethod
    def _diagnose_path_before_connecting(db_path: str) -> None:
        """
        Runs a few cheap checks before even trying to open the database, so
        that when something is wrong we can say exactly what (missing
        folder vs. no write permission vs. something else) instead of a
        generic "unable to open database file" from SQLite.
        """
        folder = Path(db_path).resolve().parent

        if not folder.exists():
            raise sqlite3.OperationalError(
                f"The folder '{folder}' does not exist. Create it first, "
                "or point db_path at a folder that does exist."
            )

        # Try to actually write a throwaway file in that folder — more
        # reliable than os.access(), which can lie on Windows/OneDrive.
        probe_file = folder / ".write_test.tmp"
        try:
            probe_file.write_text("test")
            probe_file.unlink()
        except OSError as e:
            raise sqlite3.OperationalError(
                f"Cannot write to folder '{folder}' (OS error: {e}).\n"
                "This usually means: (1) a OneDrive-synced folder that "
                "isn't fully downloaded locally yet — right-click the "
                "folder and choose 'Always keep on this device', (2) an "
                "antivirus blocking the write, or (3) missing folder "
                "permissions. Try creating a plain .txt file by hand in "
                "that same folder to confirm which one it is."
            ) from e

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone_number TEXT
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL DEFAULT 'Food'
        )""")

        # ON DELETE CASCADE: if a customer or menu item is deleted, their
        # related orders are cleaned up automatically instead of becoming
        # orphaned rows pointing at IDs that no longer exist.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE,
            FOREIGN KEY(menu_item_id) REFERENCES menu_items(id) ON DELETE CASCADE
        )""")

        # TABLE: physical restaurant tables (table #4, seats 6, etc.)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tables(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER NOT NULL UNIQUE,
            capacity INTEGER NOT NULL
        )""")

        # TABLE: reservations — links a customer to a physical table at a
        # given date/time. ON DELETE CASCADE: if the table or the customer
        # is removed, their reservations are removed with them.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            reservation_date TEXT NOT NULL,
            reservation_time TEXT NOT NULL,
            guests INTEGER NOT NULL,
            FOREIGN KEY(table_id) REFERENCES tables(id) ON DELETE CASCADE,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )""")

        self.conn.commit()

        # ------------------------------------------------------------
        # MIGRATION: add an optional reservation_id column to "orders" so
        # that food can be pre-ordered as part of a booking. Older
        # restaurant.db files created before this feature existed won't
        # have this column yet, so we add it on the fly instead of
        # requiring people to delete their existing database.
        # ------------------------------------------------------------
        cursor.execute("PRAGMA table_info(orders)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "reservation_id" not in existing_columns:
            # ON DELETE SET NULL: if the reservation is later deleted, the
            # order itself is kept (it already happened / was served) —
            # it just stops being linked to a (now gone) reservation.
            cursor.execute(
                "ALTER TABLE orders ADD COLUMN reservation_id INTEGER "
                "REFERENCES reservations(id) ON DELETE SET NULL"
            )
            self.conn.commit()

        # ------------------------------------------------------------
        # MIGRATION: add phone_number to customers (older databases won't
        # have it). It's added as a plain nullable column — existing
        # customers just won't have a phone number until someone fills
        # it in through the UI.
        # ------------------------------------------------------------
        cursor.execute("PRAGMA table_info(customers)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "phone_number" not in existing_columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN phone_number TEXT")
            self.conn.commit()

        # UNIQUE INDEX rather than a UNIQUE column constraint: SQLite treats
        # every NULL as distinct from every other NULL, so this still lets
        # existing customers (or brand new ones with no phone yet) all have
        # phone_number = NULL without violating uniqueness — it only blocks
        # two customers from sharing the same *real* phone number.
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number)"
        )

        # ------------------------------------------------------------
        # MIGRATION: add category ("Food" / "Drink") to menu_items.
        # DEFAULT 'Food' means every existing dish is safely classified
        # as food until someone re-categorizes drinks through the UI.
        # ------------------------------------------------------------
        cursor.execute("PRAGMA table_info(menu_items)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "category" not in existing_columns:
            cursor.execute("ALTER TABLE menu_items ADD COLUMN category TEXT NOT NULL DEFAULT 'Food'")
            self.conn.commit()

        # ------------------------------------------------------------
        # MIGRATION: add created_at to orders, so revenue can be broken
        # down by day/week instead of only ever showing an all-time total.
        # Existing orders placed before this migration have no real
        # timestamp on record, so they're backfilled with the migration
        # time itself — this means historical orders will all show up as
        # "placed today" the first time you run the updated app. That's a
        # one-time approximation; every order placed from now on gets its
        # real timestamp.
        # ------------------------------------------------------------
        cursor.execute("PRAGMA table_info(orders)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "created_at" not in existing_columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN created_at TEXT")
            cursor.execute(
                "UPDATE orders SET created_at = ? WHERE created_at IS NULL",
                (datetime.now().isoformat(sep=" ", timespec="seconds"),),
            )
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------
    def add_customer(self, name: str, phone_number: str | None = None) -> int:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO customers(name, phone_number) VALUES (?, ?)",
                (name, phone_number),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Phone number '{phone_number}' is already used by another customer.") from e
        self.conn.commit()
        return cursor.lastrowid

    def list_customers(self) -> list[Customer]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, phone_number FROM customers ORDER BY name")
        return [Customer(*row) for row in cursor.fetchall()]

    def update_customer(self, customer_id: int, new_name: str, new_phone_number: str | None = None) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "UPDATE customers SET name = ?, phone_number = ? WHERE id = ?",
                (new_name, new_phone_number, customer_id),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Phone number '{new_phone_number}' is already used by another customer.") from e
        self.conn.commit()

    def delete_customer(self, customer_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Menu items
    # ------------------------------------------------------------------
    def add_menu_item(self, name: str, price: float, category: str = "Food") -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO menu_items(name, price, category) VALUES (?, ?, ?)",
            (name, price, category),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_menu_items(self) -> list[MenuItem]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, price, category FROM menu_items ORDER BY category, name")
        return [MenuItem(*row) for row in cursor.fetchall()]

    def update_menu_item(self, item_id: int, new_name: str, new_price: float, new_category: str = "Food") -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE menu_items SET name = ?, price = ?, category = ? WHERE id = ?",
            (new_name, new_price, new_category, item_id),
        )
        self.conn.commit()

    def delete_menu_item(self, item_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def add_order(self, customer_id: int, menu_item_id: int, quantity: int, reservation_id: int | None = None) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO orders(customer_id, menu_item_id, quantity, reservation_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (customer_id, menu_item_id, quantity, reservation_id, datetime.now().isoformat(sep=" ", timespec="seconds")),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_orders(self) -> list[Order]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                orders.id,
                customers.name,
                menu_items.name,
                menu_items.price,
                orders.quantity,
                orders.reservation_id,
                orders.created_at
            FROM orders
            INNER JOIN customers ON orders.customer_id = customers.id
            INNER JOIN menu_items ON orders.menu_item_id = menu_items.id
            ORDER BY orders.id DESC
        """)
        return [Order(*row) for row in cursor.fetchall()]

    def list_orders_for_reservation(self, reservation_id: int) -> list[Order]:
        """All food items pre-ordered as part of a given reservation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                orders.id,
                customers.name,
                menu_items.name,
                menu_items.price,
                orders.quantity,
                orders.reservation_id,
                orders.created_at
            FROM orders
            INNER JOIN customers ON orders.customer_id = customers.id
            INNER JOIN menu_items ON orders.menu_item_id = menu_items.id
            WHERE orders.reservation_id = ?
            ORDER BY orders.id
        """, (reservation_id,))
        return [Order(*row) for row in cursor.fetchall()]

    def delete_order(self, order_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        self.conn.commit()

    def total_revenue(self) -> float:
        """Sum of (price * quantity) across every order ever placed."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(menu_items.price * orders.quantity), 0)
            FROM orders
            INNER JOIN menu_items ON orders.menu_item_id = menu_items.id
        """)
        return cursor.fetchone()[0]

    def revenue_today(self) -> float:
        """Sum of (price * quantity) for orders placed today (local date)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(menu_items.price * orders.quantity), 0)
            FROM orders
            INNER JOIN menu_items ON orders.menu_item_id = menu_items.id
            WHERE date(orders.created_at) = date('now', 'localtime')
        """)
        return cursor.fetchone()[0]

    def revenue_this_week(self) -> float:
        """Sum of (price * quantity) for orders placed in the last 7 days (including today)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(menu_items.price * orders.quantity), 0)
            FROM orders
            INNER JOIN menu_items ON orders.menu_item_id = menu_items.id
            WHERE date(orders.created_at) >= date('now', 'localtime', '-6 days')
        """)
        return cursor.fetchone()[0]

    def daily_revenue(self, days: int = 7) -> list[tuple[str, float]]:
        """
        Revenue for each of the last `days` days (oldest first), as a list
        of (YYYY-MM-DD, total) tuples. Days with no orders show up as 0.0
        rather than being skipped, so a chart plotted from this always has
        one bar per day.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT date(orders.created_at) AS day, SUM(menu_items.price * orders.quantity) AS total
            FROM orders
            INNER JOIN menu_items ON orders.menu_item_id = menu_items.id
            WHERE date(orders.created_at) >= date('now', 'localtime', ? || ' days')
            GROUP BY day
        """, (f"-{days - 1}",))
        totals_by_day = {row[0]: row[1] for row in cursor.fetchall()}

        today = datetime.now().date()
        result = []
        for i in range(days - 1, -1, -1):
            day = (today - timedelta(days=i)).isoformat()
            result.append((day, totals_by_day.get(day, 0.0)))
        return result

    # ------------------------------------------------------------------
    # Tables (the physical restaurant tables, not SQL tables!)
    # ------------------------------------------------------------------
    def add_table(self, number: int, capacity: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO tables(number, capacity) VALUES (?, ?)", (number, capacity))
        self.conn.commit()
        return cursor.lastrowid

    def list_tables(self) -> list[Table]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, number, capacity FROM tables ORDER BY number")
        return [Table(*row) for row in cursor.fetchall()]

    def update_table(self, table_id: int, number: int, capacity: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tables SET number = ?, capacity = ? WHERE id = ?",
            (number, capacity, table_id),
        )
        self.conn.commit()

    def delete_table(self, table_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tables WHERE id = ?", (table_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # Reservations (book a table for a customer, optionally with food)
    # ------------------------------------------------------------------
    def add_reservation(self, table_id: int, customer_id: int, date: str, time: str, guests: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO reservations(table_id, customer_id, reservation_date, reservation_time, guests)
               VALUES (?, ?, ?, ?, ?)""",
            (table_id, customer_id, date, time, guests),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_reservations(self) -> list[Reservation]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                reservations.id,
                tables.number,
                tables.capacity,
                customers.name,
                reservations.reservation_date,
                reservations.reservation_time,
                reservations.guests
            FROM reservations
            INNER JOIN tables ON reservations.table_id = tables.id
            INNER JOIN customers ON reservations.customer_id = customers.id
            ORDER BY reservations.reservation_date, reservations.reservation_time
        """)
        return [Reservation(*row) for row in cursor.fetchall()]

    def delete_reservation(self, reservation_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
        self.conn.commit()

    def is_table_booked(self, table_id: int, date: str, time: str) -> bool:
        """Checks whether a table already has a reservation at that exact date/time."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM reservations WHERE table_id = ? AND reservation_date = ? AND reservation_time = ?",
            (table_id, date, time),
        )
        return cursor.fetchone() is not None

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def customer_spending_report(self) -> list[CustomerSpending]:
        """
        Aggregates every order by customer phone number: how many separate
        orders they placed, how many items in total, and how much they've
        spent overall. Sorted with the biggest spenders first.

        Grouping is done on phone_number (per the requirement that the same
        person should be recognized across visits by their number) rather
        than on the internal customer id — in practice these line up 1:1
        since phone numbers are enforced unique, but grouping this way
        keeps the analysis meaningful even if that assumption ever changes.
        Customers with no phone number on file are grouped together under
        "No phone number" so they don't silently disappear from the report.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COALESCE(customers.phone_number, 'No phone number') AS phone,
                GROUP_CONCAT(DISTINCT customers.name) AS names,
                COUNT(orders.id) AS order_count,
                COALESCE(SUM(orders.quantity), 0) AS items_count,
                COALESCE(SUM(orders.quantity * menu_items.price), 0) AS total_spent
            FROM customers
            LEFT JOIN orders ON orders.customer_id = customers.id
            LEFT JOIN menu_items ON orders.menu_item_id = menu_items.id
            GROUP BY phone
            ORDER BY total_spent DESC
        """)
        return [CustomerSpending(*row) for row in cursor.fetchall()]

    def top_selling_items(self, category: str | None = None, limit: int = 10) -> list[ItemSales]:
        """
        Ranks menu items by total quantity sold (across every order ever
        placed), optionally restricted to one category ("Food" or "Drink").
        Pass category=None to rank across both at once.
        """
        cursor = self.conn.cursor()
        query = """
            SELECT
                menu_items.name,
                menu_items.category,
                COALESCE(SUM(orders.quantity), 0) AS quantity_sold,
                COALESCE(SUM(orders.quantity * menu_items.price), 0) AS revenue
            FROM menu_items
            LEFT JOIN orders ON orders.menu_item_id = menu_items.id
        """
        params: list = []
        if category is not None:
            query += " WHERE menu_items.category = ?"
            params.append(category)
        query += " GROUP BY menu_items.id ORDER BY quantity_sold DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [ItemSales(*row) for row in cursor.fetchall()]
