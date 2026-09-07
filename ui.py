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
import calendar
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import Calendar

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

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Minimum notice required before a reservation's date/time — blocks booking
# a table for "right now" or for a slot that's already passed. Change this
# if your restaurant needs a different lead time.
MIN_BOOKING_LEAD_TIME = timedelta(hours=2)


def is_valid_phone(phone: str) -> bool:
    cleaned = phone.replace(" ", "").replace("-", "")
    return bool(PHONE_PATTERN.match(cleaned))


def clean_phone(phone: str) -> str:
    """Normalizes a phone number to the compact +242XXXXXXXXX form for storage."""
    return phone.replace(" ", "").replace("-", "")


class SimpleDatePicker(tk.Frame):
    """
    A drop-in replacement for tkcalendar.DateEntry's basic API
    (.get(), .get_date(), .set_date()) that avoids a known upstream bug:
    DateEntry's built-in dropdown popup auto-closes on <FocusOut>, and
    clicking its own month/year navigation arrows can trigger a focus
    shift that gets misread as "clicked outside the popup" — closing the
    calendar instead of navigating to the next month/year
    (see tkcalendar issues #41 / #44 on GitHub).

    This widget sidesteps the bug entirely by opening the Calendar in a
    Toplevel window that WE control: it only closes when the person
    clicks "Select" (or the window's own close button), never based on
    focus changes. The month/year arrows are then just normal clicks
    inside that Toplevel, with nothing set up to misinterpret them.
    """

    def __init__(self, parent, date_pattern="%d/%m/%Y", width=11, initial_date=None, mindate=None):
        super().__init__(parent, bg=BG_COLOR)
        self.date_pattern = date_pattern
        self.mindate = mindate  # if set, dates before this can't be selected in the popup calendar
        self._date = initial_date or date.today()

        self.entry = tk.Entry(
            self, width=width, bg=FIELD_BG, fg=TEXT_COLOR, relief="flat",
            font=("Arial", 11), bd=6, state="readonly", readonlybackground=FIELD_BG,
            justify="center",
        )
        self.entry.pack(side="left")

        self.button = tk.Button(
            self, text="\U0001F4C5", command=self._open_picker, bg=FIELD_BG, fg=TEXT_COLOR,
            relief="flat", width=3, activebackground=ACCENT_BLUE, activeforeground="white",
        )
        self.button.pack(side="left", padx=(3, 0))

        self._refresh_entry_text()

    def _refresh_entry_text(self) -> None:
        self.entry.configure(state="normal")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self._date.strftime(self.date_pattern))
        self.entry.configure(state="readonly")

    def _open_picker(self) -> None:
        popup = tk.Toplevel(self)
        # Hidden until we've computed and applied its final position — this
        # is what stops it from flashing at Tk's default spawn location
        # (bottom-left corner, next to the taskbar/Start button on Windows)
        # before jumping to where it's actually supposed to appear.
        popup.withdraw()
        popup.title("Select a date")
        popup.configure(bg=BG_COLOR)
        popup.transient(self.winfo_toplevel())
        popup.resizable(False, False)

        # Show the currently selected date, unless it's before mindate (in
        # which case open on mindate instead, so the calendar doesn't try
        # to land on a month where the current selection isn't even valid).
        shown_date = self._date
        if self.mindate and shown_date < self.mindate:
            shown_date = self.mindate

        cal = Calendar(
            popup, selectmode="day",
            year=shown_date.year, month=shown_date.month, day=shown_date.day,
            mindate=self.mindate,
            background=FIELD_BG, foreground=TEXT_COLOR,
            headersbackground=FIELD_BG, headersforeground=TEXT_COLOR,
            normalbackground=FIELD_BG, normalforeground=TEXT_COLOR,
            weekendbackground=FIELD_BG, weekendforeground=TEXT_COLOR,
            othermonthbackground=BG_COLOR, othermonthforeground=TEXT_MUTED,
            selectbackground=ACCENT_BLUE, selectforeground="white",
            bordercolor=BG_COLOR,
            disabledbackground=BG_COLOR, disabledforeground=TEXT_MUTED,
        )
        cal.pack(padx=10, pady=10)

        def confirm():
            self._date = cal.selection_get()
            self._refresh_entry_text()
            popup.destroy()

        tk.Button(
            popup, text="Select", command=confirm, bg=ACCENT_BLUE, fg="white",
            relief="flat", font=("Arial", 10, "bold"),
        ).pack(pady=(0, 10))

        # Now that every widget is built, compute the popup's final size
        # and position it just below the calendar button, BEFORE showing it.
        popup.update_idletasks()
        x = self.button.winfo_rootx()
        y = self.button.winfo_rooty() + self.button.winfo_height()

        # Keep the popup on-screen if the button is near the right/bottom
        # edge, instead of letting part of it render off the visible display.
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        popup_w = popup.winfo_reqwidth()
        popup_h = popup.winfo_reqheight()
        x = min(x, screen_w - popup_w)
        y = min(y, screen_h - popup_h)

        popup.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        popup.deiconify()
        popup.grab_set()
        popup.focus_set()

    # --- API matching tkcalendar.DateEntry, so existing call sites don't need to change ---
    def get(self) -> str:
        return self._date.strftime(self.date_pattern)

    def get_date(self) -> date:
        return self._date

    def set_date(self, d) -> None:
        if isinstance(d, datetime):
            d = d.date()
        self._date = d
        self._refresh_entry_text()


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
        self.menu_category_combo = ttk.Combobox(
            form, state="readonly", width=10, values=["Food", "Drink", "Dessert", "Appetizer"]
        )
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
        try:
            self.db.add_menu_item(name, price, category)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
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
        try:
            self.db.update_menu_item(self.selected_menu_item_id, name, price, category)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
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
        self.table_number_entry = self._make_entry(form, width=8)
        self.table_number_entry.grid(row=0, column=1, padx=5)

        self._make_label(form, "Capacity:").grid(row=0, column=2, padx=5)
        self.table_capacity_entry = self._make_entry(form, width=8)
        self.table_capacity_entry.grid(row=0, column=3, padx=5)

        self._make_label(form, "Name (optional):").grid(row=0, column=4, padx=5)
        # A few common presets, but editable — any nickname is fine (e.g. "Terrace 2").
        self.table_name_combo = ttk.Combobox(
            form, width=14, values=["Family", "Couple", "VIP", "Window", "Terrace", "Bar"]
        )
        self.table_name_combo.grid(row=0, column=5, padx=5)

        self._make_button(form, "Add", self.add_table).grid(row=0, column=6, padx=5)
        self._make_button(form, "Update selected", self.update_table).grid(row=0, column=7, padx=5)
        self._make_button(form, "Delete selected", self.delete_table, bg=ACCENT_RED).grid(row=0, column=8, padx=5)

        self.tables_table = ttk.Treeview(
            parent, columns=("id", "number", "name", "capacity"), show="headings", height=15
        )
        self.tables_table.heading("id", text="ID")
        self.tables_table.heading("number", text="Table #")
        self.tables_table.heading("name", text="Name")
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
        self.table_name_combo.set(values[2])
        self.table_capacity_entry.delete(0, tk.END)
        self.table_capacity_entry.insert(0, values[3])

    def refresh_tables(self) -> None:
        self.tables_table.delete(*self.tables_table.get_children())
        for table in self.db.list_tables():
            self.tables_table.insert(
                "", tk.END, values=(table.id, table.number, table.name or "", table.capacity)
            )
        if hasattr(self, "reservation_table_combo"):
            self._refresh_reservation_comboboxes()

    def _read_table_form(self):
        number_raw = self.table_number_entry.get().strip()
        capacity_raw = self.table_capacity_entry.get().strip()
        name = self.table_name_combo.get().strip()
        if not number_raw or not capacity_raw:
            messagebox.showwarning("Error", "Table # and capacity are required.")
            return None
        if not number_raw.isdigit() or not capacity_raw.isdigit():
            messagebox.showerror("Error", "Table # and capacity must be whole numbers.")
            return None
        number, capacity = int(number_raw), int(capacity_raw)
        if capacity <= 0:
            messagebox.showerror("Error", "Capacity must be greater than zero.")
            return None
        return number, capacity, (name or None)

    def add_table(self) -> None:
        result = self._read_table_form()
        if result is None:
            return
        number, capacity, name = result
        try:
            self.db.add_table(number, capacity, name)
        except Exception:
            messagebox.showerror("Error", f"Table #{number} already exists.")
            return
        self.table_number_entry.delete(0, tk.END)
        self.table_capacity_entry.delete(0, tk.END)
        self.table_name_combo.set("")
        self.refresh_tables()

    def update_table(self) -> None:
        if self.selected_table_id is None:
            messagebox.showwarning("Error", "Select a table in the list first.")
            return
        result = self._read_table_form()
        if result is None:
            return
        number, capacity, name = result
        self.db.update_table(self.selected_table_id, number, capacity, name)
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
            self.table_name_combo.set("")
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

        self._make_label(form, "Date:").grid(row=0, column=4, padx=5)
        self.reservation_date_entry = SimpleDatePicker(
            form, date_pattern="%d/%m/%Y", width=11, mindate=date.today()
        )
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

        def table_label(t):
            nickname = f" – {t.name}" if t.name else ""
            return f"Table {t.number}{nickname} (seats {t.capacity})"

        # Store (id, capacity) together instead of parsing the capacity back
        # out of the label text later — much less fragile once names can
        # contain arbitrary text (including words like "seats" or parens).
        self.reservation_tables_by_label = {
            table_label(t): (t.id, t.capacity) for t in self.db.list_tables()
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
            reservation_datetime = datetime.strptime(f"{date_raw} {time_raw}", "%d/%m/%Y %H:%M")
        except ValueError:
            messagebox.showerror("Error", "Date must be DD/MM/YYYY and time must be HH:MM.")
            return

        # No booking in the past, and no booking for "right now" either —
        # require at least MIN_BOOKING_LEAD_TIME notice (2 hours by default).
        earliest_allowed = datetime.now() + MIN_BOOKING_LEAD_TIME
        if reservation_datetime < earliest_allowed:
            messagebox.showerror(
                "Error",
                f"Reservations must be made at least {int(MIN_BOOKING_LEAD_TIME.total_seconds() // 3600)} "
                f"hour(s) in advance. The earliest available slot is "
                f"{earliest_allowed.strftime('%d/%m/%Y %H:%M')}.",
            )
            return

        customer_id = self.reservation_customers_by_name[customer_name]
        table_id, table_capacity = self.reservation_tables_by_label[table_label]
        guests = int(guests_raw)

        if self.db.is_table_booked(table_id, date_raw, time_raw):
            messagebox.showerror("Error", "This table is already booked at that date and time.")
            return

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
        self.reservation_date_entry.set_date(datetime.now())
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
        # The Analysis tab has a lot of content (filters, stats, tables,
        # charts), so it's wrapped in a scrollable canvas — same pattern as
        # the booking form — instead of forcing the whole window taller.
        canvas = tk.Canvas(parent, borderwidth=0, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(canvas, bg=BG_COLOR)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # RESPONSIVE: the inner content frame is stretched to always match
        # the canvas's current width, so widgets packed with fill="x"/"both"
        # actually reflow when the window is resized, instead of staying
        # pinned to whatever width they had when first drawn.
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width))

        # MOUSE WHEEL SCROLLING: bind only while the pointer is actually
        # over this canvas (bind_all + unbind_all on Enter/Leave), so
        # scrolling here doesn't hijack the mouse wheel on other tabs.
        # <MouseWheel> covers Windows and macOS (trackpad two-finger
        # scroll included); <Button-4>/<Button-5> cover Linux.
        def _on_mousewheel(event):
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # No filter applied until the person picks one — None/None means
        # "all time" everywhere in refresh_analysis().
        self.analysis_start_date = None
        self.analysis_end_date = None

        # ----- Date filter -----
        self._build_analysis_filter(content)

        # ----- Headline stats -----
        stats_frame = tk.Frame(content, bg=BG_COLOR)
        stats_frame.pack(fill="x", padx=10, pady=(5, 2))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)  # responsive: columns share extra width equally

        # wraplength: at narrow window widths these labels would otherwise
        # overflow horizontally into the neighboring column instead of
        # wrapping onto a second line.
        self.stat_top_customer_label = self._make_label(stats_frame, "Top customer: —", font=("Arial", 12, "bold"), wraplength=280, justify="left")
        self.stat_top_customer_label.grid(row=0, column=0, padx=15, pady=3, sticky="w")

        self.stat_period_revenue_label = self._make_label(stats_frame, "Revenue (selected period): —", font=("Arial", 12, "bold"), wraplength=280, justify="left")
        self.stat_period_revenue_label.grid(row=0, column=1, padx=15, pady=3, sticky="w")

        self.stat_regulars_label = self._make_label(stats_frame, "Regular customers: —", font=("Arial", 12, "bold"), wraplength=280, justify="left")
        self.stat_regulars_label.grid(row=0, column=2, padx=15, pady=3, sticky="w")

        self.stat_today_revenue_label = self._make_label(stats_frame, "Today: —", font=("Arial", 11), wraplength=280, justify="left")
        self.stat_today_revenue_label.grid(row=1, column=0, padx=15, pady=3, sticky="w")

        self.stat_week_revenue_label = self._make_label(stats_frame, "This week: —", font=("Arial", 11), wraplength=280, justify="left")
        self.stat_week_revenue_label.grid(row=1, column=1, padx=15, pady=3, sticky="w")

        self.stat_alltime_revenue_label = self._make_label(stats_frame, "All-time: —", font=("Arial", 11), wraplength=280, justify="left")
        self.stat_alltime_revenue_label.grid(row=1, column=2, padx=15, pady=3, sticky="w")


        # ----- Best sellers headline strip (one line per category, built dynamically) -----
        self.bestseller_summary_frame = tk.Frame(content, bg=BG_COLOR)
        self.bestseller_summary_frame.pack(fill="x", padx=10, pady=(0, 5))

        # ----- Action buttons -----
        actions_frame = tk.Frame(content, bg=BG_COLOR)
        actions_frame.pack(fill="x", padx=10, pady=(5, 10))
        self._make_button(actions_frame, "Refresh Analysis", self.refresh_analysis).pack(side="left", padx=(0, 5))
        self._make_button(actions_frame, "Export to CSV", self.export_analysis_csv, bg=ACCENT_GREEN).pack(side="left", padx=5)
        self._make_button(actions_frame, "Export to PDF", self.export_analysis_pdf, bg=ACCENT_GREEN).pack(side="left", padx=5)

        # "Regular customer" threshold — configurable instead of a hardcoded
        # constant, so different restaurants can decide what "regular"
        # means for them (e.g. 3 orders for a small café vs. 10 for a busy
        # place). Persisted in the database via app_settings.
        self._make_label(actions_frame, "  Regular = ").pack(side="left", padx=(15, 2))
        self.regular_threshold_entry = self._make_entry(actions_frame, width=4)
        self.regular_threshold_entry.insert(0, str(self.db.get_regular_customer_threshold()))
        self.regular_threshold_entry.pack(side="left")
        self._make_label(actions_frame, "+ orders").pack(side="left", padx=(2, 5))
        self._make_button(actions_frame, "Save", self.save_regular_threshold).pack(side="left", padx=5)

        # ----- Top customers by spending (with Segment column) -----
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

        # ----- Best sellers per category: table + chart, 2 per row, built dynamically -----
        # Rebuilt on every refresh_analysis() call, since the set of
        # categories can grow any time someone adds a new one on the
        # Menu Items tab (e.g. adding "Appetizer" for the first time).
        self.categories_frame = tk.Frame(content, bg=BG_COLOR)
        self.categories_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ----- Chart: revenue trend, last 7 days (always last-7-days, regardless of the filter above) -----
        self.trend_chart_frame = tk.LabelFrame(
            content, text="Revenue — last 7 days", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        self.trend_chart_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.trend_fig, self.trend_ax, self.trend_canvas = self._make_embedded_chart(
            self.trend_chart_frame, figsize=(9, 2.6)
        )

    # ------------------------------------------------------------------
    # Date filter (Day / Month / Year / Range / All time)
    # ------------------------------------------------------------------
    def _build_analysis_filter(self, parent) -> None:
        filter_frame = tk.LabelFrame(
            parent, text="Filter", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")
        )
        filter_frame.pack(fill="x", padx=10, pady=(10, 5))

        self._make_label(filter_frame, "Period:").grid(row=0, column=0, padx=5, pady=6)
        self.analysis_mode_combo = ttk.Combobox(
            filter_frame, state="readonly", width=10,
            values=["All time", "Day", "Month", "Year", "Range"],
        )
        self.analysis_mode_combo.set("All time")
        self.analysis_mode_combo.grid(row=0, column=1, padx=5)
        self.analysis_mode_combo.bind("<<ComboboxSelected>>", lambda e: self._update_analysis_filter_widgets())

        # --- "Day" mode widget ---
        self.analysis_day_picker = SimpleDatePicker(filter_frame, date_pattern="%Y-%m-%d", width=11)

        # --- "Month" mode widgets ---
        current_year = datetime.now().year
        year_values = [str(y) for y in range(current_year - 5, current_year + 2)]

        self.analysis_month_combo = ttk.Combobox(filter_frame, state="readonly", width=11, values=MONTH_NAMES)
        self.analysis_month_combo.set(MONTH_NAMES[datetime.now().month - 1])
        self.analysis_month_year_combo = ttk.Combobox(filter_frame, state="readonly", width=6, values=year_values)
        self.analysis_month_year_combo.set(str(current_year))

        # --- "Year" mode widget ---
        self.analysis_year_combo = ttk.Combobox(filter_frame, state="readonly", width=6, values=year_values)
        self.analysis_year_combo.set(str(current_year))

        # --- "Range" mode widgets ---
        self.analysis_range_from_label = self._make_label(filter_frame, "From:")
        self.analysis_range_from = SimpleDatePicker(filter_frame, date_pattern="%Y-%m-%d", width=11)
        self.analysis_range_to_label = self._make_label(filter_frame, "To:")
        self.analysis_range_to = SimpleDatePicker(filter_frame, date_pattern="%Y-%m-%d", width=11)

        self._make_button(filter_frame, "Apply Filter", self.apply_analysis_filter).grid(row=0, column=8, padx=5)
        self._make_button(filter_frame, "Clear Filter", self.clear_analysis_filter).grid(row=0, column=9, padx=5)

        self.analysis_filter_label = self._make_label(filter_frame, "Showing: All time", font=("Arial", 9))
        self.analysis_filter_label.configure(fg=TEXT_MUTED)
        self.analysis_filter_label.grid(row=1, column=0, columnspan=10, sticky="w", padx=5, pady=(0, 6))

        self._update_analysis_filter_widgets()

    def _update_analysis_filter_widgets(self) -> None:
        """Shows only the sub-widgets relevant to the currently selected filter mode."""
        mode = self.analysis_mode_combo.get()

        # Hide everything first, then re-show only what this mode needs.
        for widget in (
            self.analysis_day_picker, self.analysis_month_combo, self.analysis_month_year_combo,
            self.analysis_year_combo, self.analysis_range_from_label, self.analysis_range_from,
            self.analysis_range_to_label, self.analysis_range_to,
        ):
            widget.grid_remove()

        if mode == "Day":
            self.analysis_day_picker.grid(row=0, column=2, padx=5)
        elif mode == "Month":
            self.analysis_month_combo.grid(row=0, column=2, padx=5)
            self.analysis_month_year_combo.grid(row=0, column=3, padx=5)
        elif mode == "Year":
            self.analysis_year_combo.grid(row=0, column=2, padx=5)
        elif mode == "Range":
            self.analysis_range_from_label.grid(row=0, column=2, padx=(5, 0))
            self.analysis_range_from.grid(row=0, column=3, padx=5)
            self.analysis_range_to_label.grid(row=0, column=4, padx=(5, 0))
            self.analysis_range_to.grid(row=0, column=5, padx=5)
        # "All time" needs no extra widget.

    def apply_analysis_filter(self) -> None:
        mode = self.analysis_mode_combo.get()

        if mode == "All time":
            self.analysis_start_date = None
            self.analysis_end_date = None
            label = "All time"

        elif mode == "Day":
            picked = self.analysis_day_picker.get_date()
            self.analysis_start_date = self.analysis_end_date = picked.isoformat()
            label = picked.strftime("%d %b %Y")

        elif mode == "Month":
            month_index = MONTH_NAMES.index(self.analysis_month_combo.get()) + 1
            year = int(self.analysis_month_year_combo.get())
            last_day = calendar.monthrange(year, month_index)[1]
            self.analysis_start_date = date(year, month_index, 1).isoformat()
            self.analysis_end_date = date(year, month_index, last_day).isoformat()
            label = f"{self.analysis_month_combo.get()} {year}"

        elif mode == "Year":
            year = int(self.analysis_year_combo.get())
            self.analysis_start_date = f"{year}-01-01"
            self.analysis_end_date = f"{year}-12-31"
            label = year

        else:  # "Range"
            start_d = self.analysis_range_from.get_date()
            end_d = self.analysis_range_to.get_date()
            if start_d > end_d:
                messagebox.showerror("Error", "The 'From' date must be on or before the 'To' date.")
                return
            self.analysis_start_date = start_d.isoformat()
            self.analysis_end_date = end_d.isoformat()
            label = f"{start_d.strftime('%d %b %Y')} \u2192 {end_d.strftime('%d %b %Y')}"

        self.analysis_filter_label.configure(text=f"Showing: {label}")
        self.refresh_analysis()

    def clear_analysis_filter(self) -> None:
        self.analysis_mode_combo.set("All time")
        self._update_analysis_filter_widgets()
        self.analysis_start_date = None
        self.analysis_end_date = None
        self.analysis_filter_label.configure(text="Showing: All time")
        self.refresh_analysis()

    def save_regular_threshold(self) -> None:
        raw = self.regular_threshold_entry.get().strip()
        if not raw.isdigit() or int(raw) < 1:
            messagebox.showerror("Error", "The threshold must be a whole number of 1 or more.")
            return
        self.db.set_regular_customer_threshold(int(raw))
        messagebox.showinfo(
            "Saved",
            f"Customers with {raw}+ orders will now be tagged 'Regular'.",
        )
        self.refresh_analysis()

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------
    def _make_embedded_chart(self, parent, figsize=(4.5, 3)):
        """Creates a matplotlib Figure/Axes styled for the dark theme, embedded in a tkinter frame."""
        fig = Figure(figsize=figsize, dpi=100, facecolor=FIELD_BG)
        ax = fig.add_subplot(111)
        self._style_dark_axes(ax)
        chart_canvas = FigureCanvasTkAgg(fig, master=parent)
        chart_canvas.draw()
        chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        return fig, ax, chart_canvas

    @staticmethod
    def _style_dark_axes(ax) -> None:
        ax.set_facecolor(FIELD_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(TEXT_MUTED)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TEXT_COLOR)

    def _draw_bestseller_chart(self, ax, chart_canvas, items, title) -> None:
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
        chart_canvas.figure.tight_layout()
        chart_canvas.draw()

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

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    def refresh_analysis(self) -> None:
        start, end = self.analysis_start_date, self.analysis_end_date

        # --- Top customers by spending (with Segment) ---
        self.analysis_customers_table.delete(*self.analysis_customers_table.get_children())
        spending_report = [
            row for row in self.db.customer_spending_report(start, end) if row.order_count > 0
        ]
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
            self.stat_top_customer_label.configure(text="Top customer: — (no orders in this period)")

        regular_count = sum(1 for row in spending_report if row.segment == "Regular")
        self.stat_regulars_label.configure(text=f"Regular customers: {regular_count}")

        # --- Revenue stats: fixed reference points + the currently selected period ---
        self.stat_today_revenue_label.configure(text=f"Today: {self.db.revenue_today():.2f}")
        self.stat_week_revenue_label.configure(text=f"This week: {self.db.revenue_this_week():.2f}")
        self.stat_alltime_revenue_label.configure(text=f"All-time: {self.db.total_revenue():.2f}")

        period_revenue = self.db.revenue_for_period(start, end) if start and end else self.db.total_revenue()
        self.stat_period_revenue_label.configure(text=f"Revenue (selected period): {period_revenue:.2f}")

        # --- Best sellers per category (dynamic — Food/Drink/Dessert/Appetizer/... whatever exists) ---
        self._rebuild_category_sections(start, end)

        # --- 7-day trend chart (always the real last 7 days, independent of the filter above) ---
        self._draw_revenue_trend_chart()

    def _rebuild_category_sections(self, start, end) -> None:
        # Torn down and rebuilt every refresh: cheap for the handful of
        # categories a restaurant menu realistically has, and it means a
        # brand new category (e.g. adding "Appetizer" for the first time)
        # shows up automatically without any extra wiring.
        for widget in self.categories_frame.winfo_children():
            widget.destroy()
        for widget in self.bestseller_summary_frame.winfo_children():
            widget.destroy()

        categories = self.db.list_categories()
        self.categories_frame.grid_columnconfigure(0, weight=1)
        self.categories_frame.grid_columnconfigure(1, weight=1)
        self.bestseller_summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

        if not categories:
            self._make_label(self.bestseller_summary_frame, "No menu items yet.").pack(side="left", padx=5)
            return

        for i, category in enumerate(categories):
            items = [
                row for row in self.db.top_selling_items(category=category, limit=10, start_date=start, end_date=end)
                if row.quantity_sold > 0
            ]

            # Headline strip entry for this category
            if items:
                summary_text = f"Most sold {category}: {items[0].name} ({items[0].quantity_sold} sold)"
            else:
                summary_text = f"Most sold {category}: — (no sales in this period)"
            # Grid instead of pack(side="left"): with several categories the
            # labels would otherwise overflow past the visible width instead
            # of wrapping. 3 per row, with the columns sharing extra width
            # (responsive) via grid_columnconfigure below.
            summary_label = self._make_label(self.bestseller_summary_frame, summary_text, font=("Arial", 11, "bold"), wraplength=280, justify="left")
            summary_label.grid(row=i // 3, column=i % 3, padx=15, pady=3, sticky="w")

            # Table + chart box for this category, 2 per row
            box = tk.LabelFrame(
                self.categories_frame, text=f"Best-selling {category}",
                bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold"),
            )
            box.grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)

            tree = ttk.Treeview(box, columns=("name", "quantity", "revenue"), show="headings", height=4)
            for col, label, width in [("name", "Item", 150), ("quantity", "Qty Sold", 80), ("revenue", "Revenue", 90)]:
                tree.heading(col, text=label)
                tree.column(col, width=width, anchor="center")
            for row in items:
                tree.insert("", tk.END, values=(row.name, row.quantity_sold, f"{row.revenue:.2f}"))
            tree.pack(fill="x", padx=5, pady=5)

            fig, ax, chart_canvas = self._make_embedded_chart(box, figsize=(4.2, 2.6))
            self._draw_bestseller_chart(ax, chart_canvas, items[:5], category)

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    def export_analysis_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Save analysis report as CSV",
        )
        if not path:
            return

        start, end = self.analysis_start_date, self.analysis_end_date
        spending_report = [row for row in self.db.customer_spending_report(start, end) if row.order_count > 0]
        categories = self.db.list_categories()

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Restaurant Analysis Report"])
                writer.writerow(["Period", self.analysis_filter_label.cget("text").replace("Showing: ", "")])
                writer.writerow([])

                writer.writerow(["Customers ranked by total spending"])
                writer.writerow(["Phone Number", "Name", "Orders", "Items Bought", "Total Spent", "Segment"])
                for row in spending_report:
                    writer.writerow([row.phone_number, row.name, row.order_count, row.items_count,
                                      f"{row.total_spent:.2f}", row.segment])

                for category in categories:
                    items = self.db.top_selling_items(category=category, limit=20, start_date=start, end_date=end)
                    writer.writerow([])
                    writer.writerow([f"Best-selling {category}"])
                    writer.writerow(["Item", "Quantity Sold", "Revenue"])
                    for row in items:
                        writer.writerow([row.name, row.quantity_sold, f"{row.revenue:.2f}"])

                writer.writerow([])
                period_revenue = self.db.revenue_for_period(start, end) if start and end else self.db.total_revenue()
                writer.writerow(["Revenue (selected period)", f"{period_revenue:.2f}"])
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

        start, end = self.analysis_start_date, self.analysis_end_date
        spending_report = [row for row in self.db.customer_spending_report(start, end) if row.order_count > 0]
        categories = self.db.list_categories()
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

        period_label = self.analysis_filter_label.cget("text").replace("Showing: ", "")
        period_revenue = self.db.revenue_for_period(start, end) if start and end else self.db.total_revenue()

        try:
            doc = SimpleDocTemplate(path, pagesize=letter)
            elements = [
                Paragraph("Restaurant Analysis Report", styles["Title"]),
                Paragraph(f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]),
                Paragraph(f"Period: {period_label}", styles["Normal"]),
                Spacer(1, 16),
                Paragraph(
                    f"Revenue — selected period: {period_revenue:.2f} | "
                    f"today: {self.db.revenue_today():.2f} | "
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
            ]

            for category in categories:
                items = self.db.top_selling_items(category=category, limit=10, start_date=start, end_date=end)
                elements.append(Spacer(1, 16))
                elements.append(Paragraph(f"Best-selling {category}", styles["Heading2"]))
                elements.append(make_table(
                    ["Item", "Quantity Sold", "Revenue"],
                    [[r.name, r.quantity_sold, f"{r.revenue:.2f}"] for r in items],
                ))

            doc.build(elements)
        except OSError as e:
            messagebox.showerror("Error", f"Could not save the PDF file: {e}")
            return

        messagebox.showinfo("Success", f"Analysis exported to {path}")
