# Restaurant Management System

A desktop application for managing restaurant customers, menu items, tables, reservations, and orders, built with **Python**, **tkinter/ttk**, and **SQLite**.

![Customers tab](screenshots/customers_tab.png)
![Menu Items tab](screenshots/menu_tab.png)
![Tables tab](screenshots/tables_tab.png)
![Reservations tab](screenshots/reservations_tab.png)
![Analysis tab](screenshots/analysis_tab.png)

## Features

- **Customers**  add, edit, and delete customer records, each with a **unique phone number** (validated as `+242XXXXXXXXX` and enforced unique at the database level) used to identify repeat customers across visits
- **Menu Items**  add, edit, and delete dishes and drinks, each tagged with a **category** (Food / Drink / Dessert / Appetizer). Item names must be unique (case-insensitive)  no accidentally adding "Pizza" twice.
- **Tables**  manage the restaurant's physical tables: a number, a seating capacity, and an optional nickname (e.g. "Family", "Couple", "VIP")
- **Reservations**  book a table for a customer at a given date (picked from a **calendar widget** that only allows today or future dates) and time, with a live conflict check (can't double-book the same table at the same slot), a minimum **2-hour advance notice** requirement (configurable via `MIN_BOOKING_LEAD_TIME` in `ui.py`), and a soft warning if the party size exceeds the table's capacity. Food can optionally be pre-ordered as part of the booking itself.
- **Orders**  place a walk-in order by linking a customer + menu item + quantity, view every order in a sortable table, and see live **total revenue**
- **Analysis**  a dedicated dashboard:
  - **Filter by Day, Month, Year, or a custom date Range** (e.g. Jan–Jun 2025, or 2024–2025), or view all-time
  - Customers ranked by total spending (grouped by phone number) within the selected period, each tagged **Regular** or **Occasional** based on order count
  - Revenue broken down by **today**, **this week**, **all-time**, and the currently **selected period**
  - Best-selling items **per category** (Food/Drink/Dessert/Appetizer/anything else you add), as both exact-number tables and embedded **matplotlib bar charts**  new categories show up automatically, no code changes needed
  - A **7-day revenue trend** chart
  - **Export the full filtered report to CSV or PDF** with one click
  - **Responsive layout**: the whole tab reflows when the window is resized, and supports **mouse wheel / two-finger trackpad scrolling**
  - Refreshes automatically whenever the tab is opened
- Deleting a customer, menu item, or table automatically removes their related orders/reservations (`ON DELETE CASCADE`); deleting a reservation keeps any food that was pre-ordered for it but unlinks it (`ON DELETE SET NULL`), so history is never silently lost
- Dark, modern UI theme built on `ttk.Style`, extended to the embedded charts, the calendar pickers, and the exported PDF
- Input validation on every form (empty fields, invalid numbers, non-positive prices/quantities, malformed dates/times, duplicate or malformed phone numbers, duplicate menu item names)

## Project structure

```
restaurant-manager/
├── database.py     # SQLite access layer (Database class + dataclasses)
├── ui.py            # tkinter/ttk interface (RestaurantApp class)
├── main.py           # entry point
├── requirements.txt
├── .gitignore
├── tests/
│   └── test_database.py   # pytest suite for the data layer
└── screenshots/
```

The database logic and the UI are kept in separate modules on purpose: `database.py` has no dependency on tkinter at all, which is what makes it possible to unit-test it directly (see `tests/`) without opening a single window.

## Getting started

```bash
git clone <this-repo-url>
cd restaurant-manager
pip install -r requirements.txt   # matplotlib, reportlab, tkcalendar (Analysis/Reservations tabs) and pytest (tests)
python main.py
```

`tkinter` and `sqlite3` ship with the Python standard library. `matplotlib` (charts), `reportlab` (PDF export), and `tkcalendar` (calendar date pickers) are the three runtime dependencies  everything else runs with just the standard library.

If you already have a `restaurant.db` from an earlier version of this project, it's migrated automatically the first time you run the updated app  no need to delete it (phone numbers and categories will just be empty/"Food", table names will be empty, and existing orders will be backfilled with the migration date, until you fill things in going forward).

## Running the tests

```bash
pytest tests/ -v
```

50 tests cover customer/menu item/order/table/reservation CRUD operations, cascading deletes, table double-booking prevention, reservation-linked pre-orders, revenue calculation (all-time, today, this week, daily breakdown, arbitrary date ranges), phone number uniqueness, duplicate menu item name prevention, table names, category listing, customer segmentation, and the configurable Regular-customer threshold  all running against an in-memory SQLite database (`:memory:`), so tests never touch `restaurant.db`.

## Tech stack

- Python 3.12
- tkinter / ttk (standard library)
- SQLite (standard library, via `sqlite3`)
- matplotlib (charts embedded in the Analysis tab)
- reportlab (PDF report export)
- tkcalendar (the underlying `Calendar` widget used by the custom date picker  see note below)
- pytest (for the test suite)

### A note on the date pickers

The calendar date pickers (Reservations date, Analysis Day/Range filters) use a small custom `SimpleDatePicker` widget (in `ui.py`) instead of `tkcalendar.DateEntry` directly, for two reasons:

1. `DateEntry`'s built-in dropdown has a known upstream bug where clicking its own month/year navigation arrows can close the whole popup instead of navigating (tkcalendar issues #41/#44). `SimpleDatePicker` opens the underlying `tkcalendar.Calendar` widget in a small window we control fully  it only closes on an explicit "Select" click, so the navigation arrows just work.
2. The popup window is kept hidden (`withdraw()`) until its final position is computed, then shown already in place  this avoids a visible "flash" at Tk's default spawn location (which can land near the taskbar/Start button on Windows) before jumping to where it's supposed to appear next to the calendar button.

The Reservations date picker also has `mindate` set to today, so past dates can't be selected in the calendar at all  combined with the 2-hour minimum lead time check on submit (which also catches "today, but too soon"), this blocks booking a table in the past.

## Possible improvements

- Search/filter bar on the Orders and Reservations tables (by customer or date range)
- A visual floor plan / calendar view for table availability
- Packaging as a standalone executable (`pyinstaller`)
- Basic user authentication if this were ever used by multiple staff members
- A longer revenue trend window (30/90 days), configurable from the Analysis tab

