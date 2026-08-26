"""
ui.py
------
All tkinter/ttk interface code for the Restaurant Management app.

Talks only to the Database class from database.py — it never writes raw
SQL itself, which keeps the interface and the data layer independent
(you could swap the storage backend without touching this file).
"""

import re
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from database import Database

# ==========================================
# COLOR PALETTE (Modern Dark)
# ==========================================
BG_COLOR = "#212529"
TEXT_COLOR = "#F8F9FA"
FIELD_BG = "#343A40"
ACCENT_BLUE = "#0D6EFD"
ACCENT_RED = "#DC3545"
ACCENT_GREEN = "#198754"
TEXT_MUTED = "#ADB5BD"

# Expected phone format: +242 followed by exactly 9 digits (Congo-Brazzaville
# mobile numbers). Spaces and dashes are stripped before checking, so users
# can type "+242 06 000 00 00" or "+242-06-000-00-00" just as easily as the
# compact form. Adjust this pattern if you need a different country's format.
PHONE_PATTERN = re.compile(r"^\+242\d{9}$")
PHONE_FORMAT_HINT = "+242XXXXXXXXX (Congo format: +242 followed by 9 digits)"


def is_valid_phone(phone: str) -> bool:
    cleaned = phone.replace(" ", "").replace("-", "")
    return bool(PHONE_PATTERN.match(cleaned))


def clean_phone(phone: str) -> str:
    """Normalizes a phone number to the compact +242XXXXXXXXX form for storage."""
    return phone.replace(" ", "").replace("-", "")


class RestaurantApp:
    """Main application window with three tabs: Customers, Menu Items, Orders."""

    def __init__(self, db_path: str = "restaurant.db"):
        self.db = Database(db_path)

        self.root = tk.Tk()
        self.root.title("Restaurant Management")
        self.root.geometry("1100x820")
        self.root.configure(bg=BG_COLOR)

        self._configure_style()
        self._build_notebook()

        # Keep track of which row is selected for edit/delete, per tab
        self.selected_customer_id = None
        self.selected_menu_item_id = None
        self.selected_order_id = None
        self.selected_table_id = None
        self.selected_reservation_id = None

        # Food items added to the booking currently being filled in, before
        # "Book Table" is clicked. List of dicts: {menu_item_id, name, price, quantity}
        self.pending_preorder_items = []

        self.refresh_customers()
        self.refresh_menu_items()
        self.refresh_tables()
        self.refresh_reservations()
        self.refresh_orders()
        self.refresh_analysis()

    def run(self) -> None:
        self.root.mainloop()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure(
            "TNotebook.Tab", background=FIELD_BG, foreground=TEXT_COLOR,
            padding=(15, 8), font=("Arial", 11, "bold"),
        )
        style.map("TNotebook.Tab", background=[("selected", ACCENT_BLUE)])

        style.configure(
            "Treeview", background=FIELD_BG, foreground=TEXT_COLOR,
            fieldbackground=FIELD_BG, rowheight=28, borderwidth=0,
        )
        style.map("Treeview", background=[("selected", ACCENT_BLUE)])
        style.configure(
            "Treeview.Heading", background=BG_COLOR, foreground=TEXT_MUTED,
            relief="flat", font=("Arial", 10, "bold"),
        )

        style.configure("TCombobox", fieldbackground=FIELD_BG, foreground=TEXT_COLOR)

    # ------------------------------------------------------------------
    # Small helper widgets shared across tabs
    # ------------------------------------------------------------------
    def _make_label(self, parent, text, **kwargs):
        kwargs.setdefault("font", ("Arial", 11, "bold"))
        return tk.Label(parent, text=text, bg=BG_COLOR, fg=TEXT_COLOR, **kwargs)

    def _make_entry(self, parent, width=25):
        return tk.Entry(
            parent, width=width, bg=FIELD_BG, fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR, relief="flat", font=("Arial", 11), bd=6,
        )

    def _make_button(self, parent, text, command, bg=ACCENT_BLUE):
        return tk.Button(
            parent, text=text, command=command, bg=bg, fg=TEXT_COLOR,
            activebackground="#0b5ed7", activeforeground=TEXT_COLOR,
            relief="flat", font=("Arial", 10, "bold"),
        )

    # ------------------------------------------------------------------
    # Notebook (tabs)
    # ------------------------------------------------------------------
    def _build_notebook(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook = notebook

        tab_customers = tk.Frame(notebook, bg=BG_COLOR)
        tab_menu = tk.Frame(notebook, bg=BG_COLOR)
        tab_tables = tk.Frame(notebook, bg=BG_COLOR)
        tab_reservations = tk.Frame(notebook, bg=BG_COLOR)
        tab_orders = tk.Frame(notebook, bg=BG_COLOR)
        tab_analysis = tk.Frame(notebook, bg=BG_COLOR)

        notebook.add(tab_customers, text="Customers")
        notebook.add(tab_menu, text="Menu Items")
        notebook.add(tab_tables, text="Tables")
        notebook.add(tab_reservations, text="Reservations")
        notebook.add(tab_orders, text="Orders")
        notebook.add(tab_analysis, text="Analysis")

        self._build_customers_tab(tab_customers)
        self._build_menu_tab(tab_menu)
        self._build_tables_tab(tab_tables)
        self._build_reservations_tab(tab_reservations)
        self._build_orders_tab(tab_orders)
        self._build_analysis_tab(tab_analysis)

        # Refresh the Analysis tab automatically whenever it's opened, so it
        # always reflects the latest orders without needing a manual click.
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event) -> None:
        current_tab_text = self.notebook.tab(self.notebook.select(), "text")
        if current_tab_text == "Analysis":
            self.refresh_analysis()

    # ==================================================================
    # CUSTOMERS TAB
    # ==================================================================
    def _build_customers_tab(self, parent) -> None:
        form = tk.Frame(parent, bg=BG_COLOR)
        form.pack(fill="x", padx=10, pady=10)

        self._make_label(form, "Name:").grid(row=0, column=0, padx=5)
        self.customer_name_entry = self._make_entry(form)
        self.customer_name_entry.grid(row=0, column=1, padx=5)

        self._make_label(form, "Phone:").grid(row=0, column=2, padx=5)
        self.customer_phone_entry = self._make_entry(form, width=18)
        self.customer_phone_entry.grid(row=0, column=3, padx=5)

        phone_hint = self._make_label(form, "e.g. +242060000001", font=("Arial", 9))
        phone_hint.configure(fg=TEXT_MUTED)
        phone_hint.grid(row=1, column=2, columnspan=2, sticky="w", padx=5)

        self._make_button(form, "Add", self.add_customer).grid(row=0, column=4, padx=5)
        self._make_button(form, "Update selected", self.update_customer).grid(row=0, column=5, padx=5)
        self._make_button(form, "Delete selected", self.delete_customer, bg=ACCENT_RED).grid(row=0, column=6, padx=5)

        self.customers_table = ttk.Treeview(parent, columns=("id", "name", "phone"), show="headings", height=15)
        self.customers_table.heading("id", text="ID")
        self.customers_table.heading("name", text="Name")
        self.customers_table.heading("phone", text="Phone Number")
        self.customers_table.column("id", width=60, anchor="center")
        self.customers_table.pack(fill="both", expand=True, padx=10, pady=10)
        self.customers_table.bind("<<TreeviewSelect>>", self._on_select_customer)

    def _on_select_customer(self, event) -> None:
        selection = self.customers_table.selection()
        if not selection:
            return
        values = self.customers_table.item(selection[0], "values")
        self.selected_customer_id = int(values[0])
        self.customer_name_entry.delete(0, tk.END)
        self.customer_name_entry.insert(0, values[1])
        self.customer_phone_entry.delete(0, tk.END)
        self.customer_phone_entry.insert(0, values[2])

    def refresh_customers(self) -> None:
        self.customers_table.delete(*self.customers_table.get_children())
        for customer in self.db.list_customers():
            self.customers_table.insert(
                "", tk.END, values=(customer.id, customer.name, customer.phone_number or "")
            )
        # also refresh the customer combobox on the Orders/Reservations tabs, if they exist yet
        if hasattr(self, "order_customer_combo"):
            self._refresh_order_comboboxes()
        if hasattr(self, "reservation_customer_combo"):
            self._refresh_reservation_comboboxes()

    def add_customer(self) -> None:
        name = self.customer_name_entry.get().strip()
        phone = self.customer_phone_entry.get().strip()
        if not name or not phone:
            messagebox.showwarning("Error", "Name and phone number are both required.")
            return
        if not is_valid_phone(phone):
            messagebox.showerror("Error", f"Phone number must look like {PHONE_FORMAT_HINT}.")
            return
        try:
            self.db.add_customer(name, clean_phone(phone))
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.customer_name_entry.delete(0, tk.END)
        self.customer_phone_entry.delete(0, tk.END)
        self.refresh_customers()

    def update_customer(self) -> None:
        if self.selected_customer_id is None:
            messagebox.showwarning("Error", "Select a customer in the table first.")
            return
        name = self.customer_name_entry.get().strip()
        phone = self.customer_phone_entry.get().strip()
        if not name or not phone:
            messagebox.showwarning("Error", "Name and phone number are both required.")
            return
        if not is_valid_phone(phone):
            messagebox.showerror("Error", f"Phone number must look like {PHONE_FORMAT_HINT}.")
            return
        try:
            self.db.update_customer(self.selected_customer_id, name, clean_phone(phone))
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.refresh_customers()

    def delete_customer(self) -> None:
        if self.selected_customer_id is None:
            messagebox.showwarning("Error", "Select a customer in the table first.")
            return
        if messagebox.askyesno("Confirm", "Delete this customer? Their past orders will be removed too."):
            self.db.delete_customer(self.selected_customer_id)
            self.selected_customer_id = None
            self.customer_name_entry.delete(0, tk.END)
            self.customer_phone_entry.delete(0, tk.END)
            self.refresh_customers()
            self.refresh_orders()

    # ==================================================================
    # MENU ITEMS TAB
    # ==================================================================
    def _build_menu_tab(self, parent) -> None:
        form = tk.Frame(parent, bg=BG_COLOR)
        form.pack(fill="x", padx=10, pady=10)

        self._make_label(form, "Name:").grid(row=0, column=0, padx=5)
        self.menu_name_entry = self._make_entry(form, width=20)
        self.menu_name_entry.grid(row=0, column=1, padx=5)

        self._make_label(form, "Price:").grid(row=0, column=2, padx=5)
        self.menu_price_entry = self._make_entry(form, width=10)
        self.menu_price_entry.grid(row=0, column=3, padx=5)

        self._make_label(form, "Category:").grid(row=0, column=4, padx=5)
        self.menu_category_combo = ttk.Combobox(form, state="readonly", width=10, values=["Food", "Drink"])
        self.menu_category_combo.set("Food")
        self.menu_category_combo.grid(row=0, column=5, padx=5)

        self._make_button(form, "Add", self.add_menu_item).grid(row=0, column=6, padx=5)
        self._make_button(form, "Update selected", self.update_menu_item).grid(row=0, column=7, padx=5)
        self._make_button(form, "Delete selected", self.delete_menu_item, bg=ACCENT_RED).grid(row=0, column=8, padx=5)

        self.menu_table = ttk.Treeview(
            parent, columns=("id", "name", "price", "category"), show="headings", height=15
        )
        self.menu_table.heading("id", text="ID")
        self.menu_table.heading("name", text="Name")
        self.menu_table.heading("price", text="Price")
        self.menu_table.heading("category", text="Category")
        self.menu_table.column("id", width=60, anchor="center")
        self.menu_table.column("category", width=90, anchor="center")
        self.menu_table.pack(fill="both", expand=True, padx=10, pady=10)
        self.menu_table.bind("<<TreeviewSelect>>", self._on_select_menu_item)

    def _on_select_menu_item(self, event) -> None:
        selection = self.menu_table.selection()
        if not selection:
            return
        values = self.menu_table.item(selection[0], "values")
        self.selected_menu_item_id = int(values[0])
        self.menu_name_entry.delete(0, tk.END)
        self.menu_name_entry.insert(0, values[1])
        self.menu_price_entry.delete(0, tk.END)
        self.menu_price_entry.insert(0, values[2])
        self.menu_category_combo.set(values[3])

    def refresh_menu_items(self) -> None:
        self.menu_table.delete(*self.menu_table.get_children())
        for item in self.db.list_menu_items():
            self.menu_table.insert(
                "", tk.END, values=(item.id, item.name, f"{item.price:.2f}", item.category)
            )
        if hasattr(self, "order_menu_combo"):
            self._refresh_order_comboboxes()
        if hasattr(self, "reservation_table_combo"):
            self._refresh_reservation_comboboxes()

    def _read_menu_form(self):
        name = self.menu_name_entry.get().strip()
        price_raw = self.menu_price_entry.get().strip()
        category = self.menu_category_combo.get()
        if not name or not price_raw or not category:
            messagebox.showwarning("Error", "All fields are required.")
            return None
        try:
            price = float(price_raw)
        except ValueError:
            messagebox.showerror("Error", "Price must be a number.")
            return None
        if price <= 0:
            messagebox.showerror("Error", "Price must be greater than zero.")
            return None
        return name, price, category

    def add_menu_item(self) -> None:
        result = self._read_menu_form()
        if result is None:
            return
        name, price, category = result
        self.db.add_menu_item(name, price, category)
        self.menu_name_entry.delete(0, tk.END)
        self.menu_price_entry.delete(0, tk.END)
        self.refresh_menu_items()

    def update_menu_item(self) -> None:
        if self.selected_menu_item_id is None:
            messagebox.showwarning("Error", "Select a menu item in the table first.")
            return
        result = self._read_menu_form()
        if result is None:
            return
        name, price, category = result
        self.db.update_menu_item(self.selected_menu_item_id, name, price, category)
        self.refresh_menu_items()

    def delete_menu_item(self) -> None:
        if self.selected_menu_item_id is None:
            messagebox.showwarning("Error", "Select a menu item in the table first.")
            return
        if messagebox.askyesno("Confirm", "Delete this menu item? Related orders will be removed too."):
            self.db.delete_menu_item(self.selected_menu_item_id)
            self.selected_menu_item_id = None
            self.menu_name_entry.delete(0, tk.END)
            self.menu_price_entry.delete(0, tk.END)
            self.refresh_menu_items()
            self.refresh_orders()

    # ==================================================================
    # TABLES TAB (the physical restaurant tables)
    # ==================================================================
    def _build_tables_tab(self, parent) -> None:
        form = tk.Frame(parent, bg=BG_COLOR)
        form.pack(fill="x", padx=10, pady=10)

        self._make_label(form, "Table #:").grid(row=0, column=0, padx=5)
        self.table_number_entry = self._make_entry(form, width=10)
        self.table_number_entry.grid(row=0, column=1, padx=5)

        self._make_label(form, "Capacity:").grid(row=0, column=2, padx=5)
        self.table_capacity_entry = self._make_entry(form, width=10)
        self.table_capacity_entry.grid(row=0, column=3, padx=5)

        self._make_button(form, "Add", self.add_table).grid(row=0, column=4, padx=5)
        self._make_button(form, "Update selected", self.update_table).grid(row=0, column=5, padx=5)
        self._make_button(form, "Delete selected", self.delete_table, bg=ACCENT_RED).grid(row=0, column=6, padx=5)

        self.tables_table = ttk.Treeview(parent, columns=("id", "number", "capacity"), show="headings", height=15)
        self.tables_table.heading("id", text="ID")
        self.tables_table.heading("number", text="Table #")
        self.tables_table.heading("capacity", text="Capacity (seats)")
        self.tables_table.column("id", width=60, anchor="center")
        self.tables_table.pack(fill="both", expand=True, padx=10, pady=10)
        self.tables_table.bind("<<TreeviewSelect>>", self._on_select_table)

    def _on_select_table(self, event) -> None:
        selection = self.tables_table.selection()
        if not selection:
            return
        values = self.tables_table.item(selection[0], "values")
        self.selected_table_id = int(values[0])
        self.table_number_entry.delete(0, tk.END)
        self.table_number_entry.insert(0, values[1])
        self.table_capacity_entry.delete(0, tk.END)
        self.table_capacity_entry.insert(0, values[2])

    def refresh_tables(self) -> None:
        self.tables_table.delete(*self.tables_table.get_children())
        for table in self.db.list_tables():
            self.tables_table.insert("", tk.END, values=(table.id, table.number, table.capacity))
        if hasattr(self, "reservation_table_combo"):
            self._refresh_reservation_comboboxes()

    def _read_table_form(self):
        number_raw = self.table_number_entry.get().strip()
        capacity_raw = self.table_capacity_entry.get().strip()
        if not number_raw or not capacity_raw:
            messagebox.showwarning("Error", "All fields are required.")
            return None
        if not number_raw.isdigit() or not capacity_raw.isdigit():
            messagebox.showerror("Error", "Table # and capacity must be whole numbers.")
            return None
        number, capacity = int(number_raw), int(capacity_raw)
        if capacity <= 0:
            messagebox.showerror("Error", "Capacity must be greater than zero.")
            return None
        return number, capacity

    def add_table(self) -> None:
        result = self._read_table_form()
        if result is None:
            return
        number, capacity = result
        try:
            self.db.add_table(number, capacity)
        except Exception:
            messagebox.showerror("Error", f"Table #{number} already exists.")
            return
        self.table_number_entry.delete(0, tk.END)
        self.table_capacity_entry.delete(0, tk.END)
        self.refresh_tables()

    def update_table(self) -> None:
        if self.selected_table_id is None:
            messagebox.showwarning("Error", "Select a table in the list first.")
            return
        result = self._read_table_form()
        if result is None:
            return
        number, capacity = result
        self.db.update_table(self.selected_table_id, number, capacity)
        self.refresh_tables()

    def delete_table(self) -> None:
        if self.selected_table_id is None:
            messagebox.showwarning("Error", "Select a table in the list first.")
            return
        if messagebox.askyesno("Confirm", "Delete this table? Its reservations will be removed too."):
            self.db.delete_table(self.selected_table_id)
            self.selected_table_id = None
            self.table_number_entry.delete(0, tk.END)
            self.table_capacity_entry.delete(0, tk.END)
            self.refresh_tables()
            self.refresh_reservations()

    # ==================================================================
    # RESERVATIONS TAB (book a table, optionally pre-order food)
    # ==================================================================
    def _build_reservations_tab(self, parent) -> None:
        # ----- Booking form -----
        form = tk.Frame(parent, bg=BG_COLOR)
        form.pack(fill="x", padx=10, pady=(10, 5))

        self._make_label(form, "Customer:").grid(row=0, column=0, padx=5, pady=3)
        self.reservation_customer_combo = ttk.Combobox(form, state="readonly", width=18)
        self.reservation_customer_combo.grid(row=0, column=1, padx=5)

        self._make_label(form, "Table:").grid(row=0, column=2, padx=5)
        self.reservation_table_combo = ttk.Combobox(form, state="readonly", width=18)
        self.reservation_table_combo.grid(row=0, column=3, padx=5)

        self._make_label(form, "Date (DD/MM/YYYY):").grid(row=0, column=4, padx=5)
        self.reservation_date_entry = self._make_entry(form, width=12)
        self.reservation_date_entry.grid(row=0, column=5, padx=5)

        self._make_label(form, "Time (HH:MM):").grid(row=1, column=4, padx=5, pady=3)
        self.reservation_time_entry = self._make_entry(form, width=12)
        self.reservation_time_entry.grid(row=1, column=5, padx=5)

        self._make_label(form, "Guests:").grid(row=1, column=0, padx=5)
        self.reservation_guests_entry = self._make_entry(form, width=6)
        self.reservation_guests_entry.grid(row=1, column=1, padx=5, sticky="w")

        # ----- Optional food pre-order, added to the booking about to be created -----
        preorder_frame = tk.LabelFrame(
            parent, text="Pre-order food for this booking (optional)",
            bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold"),
        )
        preorder_frame.pack(fill="x", padx=10, pady=5)

        self._make_label(preorder_frame, "Menu Item:").grid(row=0, column=0, padx=5, pady=5)
        self.preorder_menu_combo = ttk.Combobox(preorder_frame, state="readonly", width=18)
        self.preorder_menu_combo.grid(row=0, column=1, padx=5)

        self._make_label(preorder_frame, "Qty:").grid(row=0, column=2, padx=5)
        self.preorder_quantity_entry = self._make_entry(preorder_frame, width=6)
        self.preorder_quantity_entry.grid(row=0, column=3, padx=5)

        self._make_button(preorder_frame, "Add item", self.add_preorder_item).grid(row=0, column=4, padx=5)
        self._make_button(preorder_frame, "Remove item", self.remove_preorder_item, bg=ACCENT_RED).grid(row=0, column=5, padx=5)

        self.preorder_cart_table = ttk.Treeview(
            preorder_frame, columns=("name", "quantity", "price"), show="headings", height=3,
        )
        self.preorder_cart_table.heading("name", text="Item")
        self.preorder_cart_table.heading("quantity", text="Qty")
        self.preorder_cart_table.heading("price", text="Unit Price")
        self.preorder_cart_table.column("quantity", width=60, anchor="center")
        self.preorder_cart_table.column("price", width=90, anchor="center")
        self.preorder_cart_table.grid(row=1, column=0, columnspan=6, padx=5, pady=5, sticky="ew")

        button_row = tk.Frame(parent, bg=BG_COLOR)
        button_row.pack(fill="x", padx=10, pady=(0, 5))
        self._make_button(button_row, "Book Table", self.add_reservation).pack(side="left", padx=5)
        self._make_button(button_row, "Delete selected booking", self.delete_reservation, bg=ACCENT_RED).pack(side="left", padx=5)

        # ----- List of all reservations -----
        self.reservations_table = ttk.Treeview(
            parent, columns=("id", "table", "customer", "date", "time", "guests"),
            show="headings", height=8,
        )
        for col, label, width in [
            ("id", "ID", 50), ("table", "Table #", 70), ("customer", "Customer", 140),
            ("date", "Date", 100), ("time", "Time", 70), ("guests", "Guests", 60),
        ]:
            self.reservations_table.heading(col, text=label)
            self.reservations_table.column(col, width=width, anchor="center")
        self.reservations_table.pack(fill="both", expand=True, padx=10, pady=5)
        self.reservations_table.bind("<<TreeviewSelect>>", self._on_select_reservation)

        self._make_label(parent, "Pre-ordered food for selected booking:").pack(anchor="w", padx=10)
        self.reservation_preorder_view = ttk.Treeview(
            parent, columns=("name", "quantity", "price", "total"), show="headings", height=3,
        )
        for col, label in [("name", "Item"), ("quantity", "Qty"), ("price", "Unit Price"), ("total", "Total")]:
            self.reservation_preorder_view.heading(col, text=label)
        self.reservation_preorder_view.pack(fill="x", padx=10, pady=(0, 10))

    def _refresh_reservation_comboboxes(self) -> None:
        self.reservation_customers_by_name = {c.name: c.id for c in self.db.list_customers()}
        self.reservation_tables_by_label = {
            f"Table {t.number} (seats {t.capacity})": t.id for t in self.db.list_tables()
        }
        self.reservation_customer_combo["values"] = list(self.reservation_customers_by_name.keys())
        self.reservation_table_combo["values"] = list(self.reservation_tables_by_label.keys())

        self.preorder_menu_items_by_name = {m.name: (m.id, m.price) for m in self.db.list_menu_items()}
        self.preorder_menu_combo["values"] = list(self.preorder_menu_items_by_name.keys())

    def _on_select_reservation(self, event) -> None:
        selection = self.reservations_table.selection()
        if not selection:
            return
        values = self.reservations_table.item(selection[0], "values")
        self.selected_reservation_id = int(values[0])

        self.reservation_preorder_view.delete(*self.reservation_preorder_view.get_children())
        for order in self.db.list_orders_for_reservation(self.selected_reservation_id):
            self.reservation_preorder_view.insert(
                "", tk.END,
                values=(order.menu_item_name, order.quantity, f"{order.price:.2f}", f"{order.total:.2f}"),
            )

    def refresh_reservations(self) -> None:
        self.reservations_table.delete(*self.reservations_table.get_children())
        for reservation in self.db.list_reservations():
            self.reservations_table.insert(
                "", tk.END,
                values=(reservation.id, reservation.table_number, reservation.customer_name,
                        reservation.date, reservation.time, reservation.guests),
            )
        self.reservation_preorder_view.delete(*self.reservation_preorder_view.get_children())

    # ----- Pre-order cart (used while filling in a new booking) -----
    def add_preorder_item(self) -> None:
        name = self.preorder_menu_combo.get()
        quantity_raw = self.preorder_quantity_entry.get().strip()
        if not name or not quantity_raw:
            messagebox.showwarning("Error", "Pick a menu item and a quantity first.")
            return
        if not quantity_raw.isdigit() or int(quantity_raw) <= 0:
            messagebox.showerror("Error", "Quantity must be a positive whole number.")
            return

        menu_item_id, price = self.preorder_menu_items_by_name[name]
        self.pending_preorder_items.append(
            {"menu_item_id": menu_item_id, "name": name, "price": price, "quantity": int(quantity_raw)}
        )
        self.preorder_quantity_entry.delete(0, tk.END)
        self._refresh_preorder_cart_view()

    def remove_preorder_item(self) -> None:
        selection = self.preorder_cart_table.selection()
        if not selection:
            messagebox.showwarning("Error", "Select an item in the pre-order cart first.")
            return
        index = self.preorder_cart_table.index(selection[0])
        del self.pending_preorder_items[index]
        self._refresh_preorder_cart_view()

    def _refresh_preorder_cart_view(self) -> None:
        self.preorder_cart_table.delete(*self.preorder_cart_table.get_children())
        for item in self.pending_preorder_items:
            self.preorder_cart_table.insert(
                "", tk.END, values=(item["name"], item["quantity"], f"{item['price']:.2f}")
            )

    def add_reservation(self) -> None:
        customer_name = self.reservation_customer_combo.get()
        table_label = self.reservation_table_combo.get()
        date_raw = self.reservation_date_entry.get().strip()
        time_raw = self.reservation_time_entry.get().strip()
        guests_raw = self.reservation_guests_entry.get().strip()

        if not customer_name or not table_label or not date_raw or not time_raw or not guests_raw:
            messagebox.showwarning("Error", "Please fill in all fields.")
            return
        if not guests_raw.isdigit() or int(guests_raw) <= 0:
            messagebox.showerror("Error", "Guests must be a positive whole number.")
            return

        # Validate the date/time format up front, the same way the rest of
        # the app validates dates, instead of letting a bad string slip
        # silently into the database.
        try:
            datetime.strptime(date_raw, "%d/%m/%Y")
            datetime.strptime(time_raw, "%H:%M")
        except ValueError:
            messagebox.showerror("Error", "Date must be DD/MM/YYYY and time must be HH:MM.")
            return

        customer_id = self.reservation_customers_by_name[customer_name]
        table_id = self.reservation_tables_by_label[table_label]
        guests = int(guests_raw)

        if self.db.is_table_booked(table_id, date_raw, time_raw):
            messagebox.showerror("Error", "This table is already booked at that date and time.")
            return

        table_capacity = int(table_label.split("seats ")[1].rstrip(")"))
        if guests > table_capacity:
            if not messagebox.askyesno(
                "Capacity warning",
                f"This table only seats {table_capacity}, but {guests} guests were entered. Book anyway?",
            ):
                return

        reservation_id = self.db.add_reservation(table_id, customer_id, date_raw, time_raw, guests)

        # Save any food added to the pre-order cart, now linked to this booking
        for item in self.pending_preorder_items:
            self.db.add_order(customer_id, item["menu_item_id"], item["quantity"], reservation_id=reservation_id)

        self.pending_preorder_items = []
        self._refresh_preorder_cart_view()
        self.reservation_date_entry.delete(0, tk.END)
        self.reservation_time_entry.delete(0, tk.END)
        self.reservation_guests_entry.delete(0, tk.END)

        self.refresh_reservations()
        self.refresh_orders()

    def delete_reservation(self) -> None:
        if self.selected_reservation_id is None:
            messagebox.showwarning("Error", "Select a booking in the list first.")
            return
        if messagebox.askyesno(
            "Confirm", "Delete this booking? Any pre-ordered food stays on record but is unlinked from it."
        ):
            self.db.delete_reservation(self.selected_reservation_id)
            self.selected_reservation_id = None
            self.refresh_reservations()
            self.refresh_orders()

    # ==================================================================
    # ORDERS TAB
    # ==================================================================
    def _build_orders_tab(self, parent) -> None:
        form = tk.Frame(parent, bg=BG_COLOR)
        form.pack(fill="x", padx=10, pady=10)

        self._make_label(form, "Customer:").grid(row=0, column=0, padx=5)
        self.order_customer_combo = ttk.Combobox(form, state="readonly", width=20)
        self.order_customer_combo.grid(row=0, column=1, padx=5)

        self._make_label(form, "Menu Item:").grid(row=0, column=2, padx=5)
        self.order_menu_combo = ttk.Combobox(form, state="readonly", width=20)
        self.order_menu_combo.grid(row=0, column=3, padx=5)

        self._make_label(form, "Quantity:").grid(row=0, column=4, padx=5)
        self.order_quantity_entry = self._make_entry(form, width=6)
        self.order_quantity_entry.grid(row=0, column=5, padx=5)

        self._make_button(form, "Place Order", self.add_order).grid(row=0, column=6, padx=5)
        self._make_button(form, "Delete selected", self.delete_order, bg=ACCENT_RED).grid(row=0, column=7, padx=5)

        self.orders_table = ttk.Treeview(
            parent, columns=("id", "customer", "menu_item", "price", "quantity", "total"),
            show="headings", height=13,
        )
        for col, label, width in [
            ("id", "ID", 50), ("customer", "Customer", 150), ("menu_item", "Menu Item", 150),
            ("price", "Unit Price", 90), ("quantity", "Qty", 60), ("total", "Total", 90),
        ]:
            self.orders_table.heading(col, text=label)
            self.orders_table.column(col, width=width, anchor="center")
        self.orders_table.pack(fill="both", expand=True, padx=10, pady=10)
        self.orders_table.bind("<<TreeviewSelect>>", self._on_select_order)

        self.revenue_label = self._make_label(parent, "Total revenue: 0.00", font=("Arial", 13, "bold"))
        self.revenue_label.pack(anchor="e", padx=15, pady=(0, 10))

    def _refresh_order_comboboxes(self) -> None:
        self.customers_by_name = {c.name: c.id for c in self.db.list_customers()}
        self.menu_items_by_name = {m.name: (m.id, m.price) for m in self.db.list_menu_items()}
        self.order_customer_combo["values"] = list(self.customers_by_name.keys())
        self.order_menu_combo["values"] = list(self.menu_items_by_name.keys())

    def _on_select_order(self, event) -> None:
        selection = self.orders_table.selection()
        if not selection:
            return
        values = self.orders_table.item(selection[0], "values")
        self.selected_order_id = int(values[0])

    def refresh_orders(self) -> None:
        self.orders_table.delete(*self.orders_table.get_children())
        for order in self.db.list_orders():
            self.orders_table.insert(
                "", tk.END,
                values=(order.id, order.customer_name, order.menu_item_name,
                        f"{order.price:.2f}", order.quantity, f"{order.total:.2f}"),
            )
        self.revenue_label.configure(text=f"Total revenue: {self.db.total_revenue():.2f}")

    def add_order(self) -> None:
        customer_name = self.order_customer_combo.get()
        menu_item_name = self.order_menu_combo.get()
        quantity_raw = self.order_quantity_entry.get().strip()

        if not customer_name or not menu_item_name or not quantity_raw:
            messagebox.showwarning("Error", "Please fill in all fields.")
            return
        if not quantity_raw.isdigit() or int(quantity_raw) <= 0:
            messagebox.showerror("Error", "Quantity must be a positive whole number.")
            return

        customer_id = self.customers_by_name[customer_name]
        menu_item_id, _ = self.menu_items_by_name[menu_item_name]

        self.db.add_order(customer_id, menu_item_id, int(quantity_raw))
        self.order_quantity_entry.delete(0, tk.END)
        self.refresh_orders()

    def delete_order(self) -> None:
        if self.selected_order_id is None:
            messagebox.showwarning("Error", "Select an order in the table first.")
            return
        if messagebox.askyesno("Confirm", "Delete this order?"):
            self.db.delete_order(self.selected_order_id)
            self.selected_order_id = None
            self.refresh_orders()

    # ==================================================================
    # ANALYSIS TAB
    # ==================================================================
    def _build_analysis_tab(self, parent) -> None:
        # The Analysis tab now has a lot of content (stats, tables, charts),
        # so it's wrapped in a scrollable canvas — the same pattern used for
        # the booking form — instead of forcing the whole window taller.
        canvas = tk.Canvas(parent, borderwidth=0, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(canvas, bg=BG_COLOR)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # ----- Headline stats, row 1 -----
        stats_frame = tk.Frame(content, bg=BG_COLOR)
        stats_frame.pack(fill="x", padx=10, pady=(10, 2))

        self.stat_top_customer_label = self._make_label(stats_frame, "Top customer: —", font=("Arial", 12, "bold"))
        self.stat_top_customer_label.grid(row=0, column=0, padx=15, pady=3, sticky="w")

        self.stat_top_food_label = self._make_label(stats_frame, "Most sold food: —", font=("Arial", 12, "bold"))
        self.stat_top_food_label.grid(row=0, column=1, padx=15, pady=3, sticky="w")

        self.stat_top_drink_label = self._make_label(stats_frame, "Most sold drink: —", font=("Arial", 12, "bold"))
        self.stat_top_drink_label.grid(row=0, column=2, padx=15, pady=3, sticky="w")

        # ----- Headline stats, row 2 (revenue by period + segmentation) -----
        self.stat_today_revenue_label = self._make_label(stats_frame, "Today: —", font=("Arial", 11))
        self.stat_today_revenue_label.grid(row=1, column=0, padx=15, pady=3, sticky="w")

        self.stat_week_revenue_label = self._make_label(stats_frame, "This week: —", font=("Arial", 11))
        self.stat_week_revenue_label.grid(row=1, column=1, padx=15, pady=3, sticky="w")

        self.stat_regulars_label = self._make_label(stats_frame, "Regular customers: —", font=("Arial", 11))
        self.stat_regulars_label.grid(row=1, column=2, padx=15, pady=3, sticky="w")

        # ----- Action buttons -----
        actions_frame = tk.Frame(content, bg=BG_COLOR)
        actions_frame.pack(fill="x", padx=10, pady=(5, 10))
        self._make_button(actions_frame, "Refresh Analysis", self.refresh_analysis).pack(side="left", padx=(0, 5))
        self._make_button(actions_frame, "Export to CSV", self.export_analysis_csv, bg=ACCENT_GREEN).pack(side="left", padx=5)
        self._make_button(actions_frame, "Export to PDF", self.export_analysis_pdf, bg=ACCENT_GREEN).pack(side="left", padx=5)

        # ----- Top customers by spending (now with a Segment column) -----
        self._make_label(content, "Customers ranked by total spending:").pack(anchor="w", padx=10)
        self.analysis_customers_table = ttk.Treeview(
            content, columns=("phone", "name", "orders", "items", "spent", "segment"), show="headings", height=8,
        )
        for col, label, width in [
            ("phone", "Phone Number", 130), ("name", "Name", 160), ("orders", "Orders", 60),
            ("items", "Items Bought", 90), ("spent", "Total Spent", 100), ("segment", "Segment", 90),
        ]:
            self.analysis_customers_table.heading(col, text=label)
            self.analysis_customers_table.column(col, width=width, anchor="center")
        self.analysis_customers_table.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ----- Best sellers: food vs drink, side by side (exact numbers) -----
        bestsellers_frame = tk.Frame(content, bg=BG_COLOR)
        bestsellers_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        food_frame = tk.LabelFrame(
            bestsellers_frame, text="Best-selling food", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        food_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.analysis_food_table = ttk.Treeview(
            food_frame, columns=("name", "quantity", "revenue"), show="headings", height=5,
        )
        for col, label, width in [("name", "Item", 160), ("quantity", "Qty Sold", 90), ("revenue", "Revenue", 100)]:
            self.analysis_food_table.heading(col, text=label)
            self.analysis_food_table.column(col, width=width, anchor="center")
        self.analysis_food_table.pack(fill="both", expand=True, padx=5, pady=5)

        drink_frame = tk.LabelFrame(
            bestsellers_frame, text="Best-selling drinks", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        drink_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self.analysis_drink_table = ttk.Treeview(
            drink_frame, columns=("name", "quantity", "revenue"), show="headings", height=5,
        )
        for col, label, width in [("name", "Item", 160), ("quantity", "Qty Sold", 90), ("revenue", "Revenue", 100)]:
            self.analysis_drink_table.heading(col, text=label)
            self.analysis_drink_table.column(col, width=width, anchor="center")
        self.analysis_drink_table.pack(fill="both", expand=True, padx=5, pady=5)

        # ----- Charts: top food / top drink quantities, side by side -----
        charts_frame = tk.Frame(content, bg=BG_COLOR)
        charts_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.food_chart_frame = tk.LabelFrame(
            charts_frame, text="Top 5 food (chart)", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        self.food_chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.food_fig, self.food_ax, self.food_canvas = self._make_embedded_chart(self.food_chart_frame)

        self.drink_chart_frame = tk.LabelFrame(
            charts_frame, text="Top 5 drinks (chart)", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        self.drink_chart_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.drink_fig, self.drink_ax, self.drink_canvas = self._make_embedded_chart(self.drink_chart_frame)

        # ----- Chart: revenue trend, last 7 days -----
        self.trend_chart_frame = tk.LabelFrame(
            content, text="Revenue — last 7 days", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        self.trend_chart_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.trend_fig, self.trend_ax, self.trend_canvas = self._make_embedded_chart(
            self.trend_chart_frame, figsize=(9, 2.6)
        )

    def _make_embedded_chart(self, parent, figsize=(4.5, 3)):
        """Creates a matplotlib Figure/Axes styled for the dark theme, embedded in a tkinter frame."""
        fig = Figure(figsize=figsize, dpi=100, facecolor=FIELD_BG)
        ax = fig.add_subplot(111)
        self._style_dark_axes(ax)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        return fig, ax, canvas

    @staticmethod
    def _style_dark_axes(ax) -> None:
        ax.set_facecolor(FIELD_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(TEXT_MUTED)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TEXT_COLOR)

    def refresh_analysis(self) -> None:
        # --- Top customers by spending (with Segment) ---
        self.analysis_customers_table.delete(*self.analysis_customers_table.get_children())
        spending_report = [row for row in self.db.customer_spending_report() if row.order_count > 0]
        for row in spending_report:
            self.analysis_customers_table.insert(
                "", tk.END,
                values=(row.phone_number, row.name, row.order_count, row.items_count,
                        f"{row.total_spent:.2f}", row.segment),
            )

        if spending_report:
            top = spending_report[0]
            self.stat_top_customer_label.configure(text=f"Top customer: {top.name} ({top.total_spent:.2f} spent)")
        else:
            self.stat_top_customer_label.configure(text="Top customer: — (no orders yet)")

        regular_count = sum(1 for row in spending_report if row.segment == "Regular")
        self.stat_regulars_label.configure(text=f"Regular customers: {regular_count}")

        # --- Revenue by period ---
        self.stat_today_revenue_label.configure(text=f"Today: {self.db.revenue_today():.2f}")
        self.stat_week_revenue_label.configure(text=f"This week: {self.db.revenue_this_week():.2f}")

        # --- Best-selling food ---
        self.analysis_food_table.delete(*self.analysis_food_table.get_children())
        top_food = [row for row in self.db.top_selling_items(category="Food", limit=10) if row.quantity_sold > 0]
        for row in top_food:
            self.analysis_food_table.insert("", tk.END, values=(row.name, row.quantity_sold, f"{row.revenue:.2f}"))
        if top_food:
            self.stat_top_food_label.configure(text=f"Most sold food: {top_food[0].name} ({top_food[0].quantity_sold} sold)")
        else:
            self.stat_top_food_label.configure(text="Most sold food: — (no orders yet)")

        # --- Best-selling drinks ---
        self.analysis_drink_table.delete(*self.analysis_drink_table.get_children())
        top_drinks = [row for row in self.db.top_selling_items(category="Drink", limit=10) if row.quantity_sold > 0]
        for row in top_drinks:
            self.analysis_drink_table.insert("", tk.END, values=(row.name, row.quantity_sold, f"{row.revenue:.2f}"))
        if top_drinks:
            self.stat_top_drink_label.configure(text=f"Most sold drink: {top_drinks[0].name} ({top_drinks[0].quantity_sold} sold)")
        else:
            self.stat_top_drink_label.configure(text="Most sold drink: — (no orders yet)")

        # --- Charts ---
        self._draw_bestseller_chart(self.food_ax, self.food_canvas, top_food[:5], "Food")
        self._draw_bestseller_chart(self.drink_ax, self.drink_canvas, top_drinks[:5], "Drinks")
        self._draw_revenue_trend_chart()

    def _draw_bestseller_chart(self, ax, canvas, items, title) -> None:
        ax.clear()
        self._style_dark_axes(ax)
        if items:
            names = [item.name for item in reversed(items)]
            quantities = [item.quantity_sold for item in reversed(items)]
            bars = ax.barh(names, quantities, color=ACCENT_BLUE)
            ax.bar_label(bars, padding=3, color=TEXT_COLOR, fontsize=8)
        else:
            ax.text(0.5, 0.5, "No sales yet", ha="center", va="center", color=TEXT_MUTED, transform=ax.transAxes)
        ax.set_title(f"Top {title} by quantity sold", fontsize=9)
        canvas.figure.tight_layout()
        canvas.draw()

    def _draw_revenue_trend_chart(self) -> None:
        self.trend_ax.clear()
        self._style_dark_axes(self.trend_ax)
        daily = self.db.daily_revenue(days=7)
        labels = [datetime.strptime(day, "%Y-%m-%d").strftime("%a %d") for day, _ in daily]
        values = [total for _, total in daily]
        self.trend_ax.bar(labels, values, color=ACCENT_GREEN)
        self.trend_ax.set_title("Daily revenue — last 7 days", fontsize=9)
        self.trend_canvas.figure.tight_layout()
        self.trend_canvas.draw()

    # ----- Exports -----
    def export_analysis_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Save analysis report as CSV",
        )
        if not path:
            return

        spending_report = [row for row in self.db.customer_spending_report() if row.order_count > 0]
        top_food = self.db.top_selling_items(category="Food", limit=20)
        top_drinks = self.db.top_selling_items(category="Drink", limit=20)

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Customers ranked by total spending"])
                writer.writerow(["Phone Number", "Name", "Orders", "Items Bought", "Total Spent", "Segment"])
                for row in spending_report:
                    writer.writerow([row.phone_number, row.name, row.order_count, row.items_count,
                                      f"{row.total_spent:.2f}", row.segment])

                writer.writerow([])
                writer.writerow(["Best-selling food"])
                writer.writerow(["Item", "Quantity Sold", "Revenue"])
                for row in top_food:
                    writer.writerow([row.name, row.quantity_sold, f"{row.revenue:.2f}"])

                writer.writerow([])
                writer.writerow(["Best-selling drinks"])
                writer.writerow(["Item", "Quantity Sold", "Revenue"])
                for row in top_drinks:
                    writer.writerow([row.name, row.quantity_sold, f"{row.revenue:.2f}"])

                writer.writerow([])
                writer.writerow(["Revenue today", f"{self.db.revenue_today():.2f}"])
                writer.writerow(["Revenue this week", f"{self.db.revenue_this_week():.2f}"])
                writer.writerow(["Revenue all-time", f"{self.db.total_revenue():.2f}"])
        except OSError as e:
            messagebox.showerror("Error", f"Could not save the CSV file: {e}")
            return

        messagebox.showinfo("Success", f"Analysis exported to {path}")

    def export_analysis_pdf(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], title="Save analysis report as PDF",
        )
        if not path:
            return

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            messagebox.showerror(
                "Error", "PDF export requires the 'reportlab' package.\nInstall it with: pip install reportlab"
            )
            return

        spending_report = [row for row in self.db.customer_spending_report() if row.order_count > 0]
        top_food = self.db.top_selling_items(category="Food", limit=10)
        top_drinks = self.db.top_selling_items(category="Drink", limit=10)
        styles = getSampleStyleSheet()

        def make_table(headers, rows):
            data = [headers] + rows
            table = Table(data, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#212529")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]))
            return table

        try:
            doc = SimpleDocTemplate(path, pagesize=letter)
            elements = [
                Paragraph("Restaurant Analysis Report", styles["Title"]),
                Paragraph(f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]),
                Spacer(1, 16),
                Paragraph(
                    f"Revenue — today: {self.db.revenue_today():.2f} | "
                    f"this week: {self.db.revenue_this_week():.2f} | "
                    f"all-time: {self.db.total_revenue():.2f}",
                    styles["Normal"],
                ),
                Spacer(1, 16),
                Paragraph("Customers ranked by total spending", styles["Heading2"]),
                make_table(
                    ["Phone Number", "Name", "Orders", "Items", "Total Spent", "Segment"],
                    [[r.phone_number, r.name, r.order_count, r.items_count, f"{r.total_spent:.2f}", r.segment]
                     for r in spending_report],
                ),
                Spacer(1, 16),
                Paragraph("Best-selling food", styles["Heading2"]),
                make_table(
                    ["Item", "Quantity Sold", "Revenue"],
                    [[r.name, r.quantity_sold, f"{r.revenue:.2f}"] for r in top_food],
                ),
                Spacer(1, 16),
                Paragraph("Best-selling drinks", styles["Heading2"]),
                make_table(
                    ["Item", "Quantity Sold", "Revenue"],
                    [[r.name, r.quantity_sold, f"{r.revenue:.2f}"] for r in top_drinks],
                ),
            ]
            doc.build(elements)
        except OSError as e:
            messagebox.showerror("Error", f"Could not save the PDF file: {e}")
            return

        messagebox.showinfo("Success", f"Analysis exported to {path}")
