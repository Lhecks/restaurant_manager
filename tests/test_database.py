"""
test_database.py
------------------
Unit tests for the Database class (database.py).

Uses an in-memory SQLite database (":memory:") so every test starts from
a clean slate and nothing touches disk or a real restaurant.db file.
"""

import sys
import os

# Allow "import database" when running pytest from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from database import Database


@pytest.fixture
def db():
    """Fresh in-memory database for each test."""
    database = Database(":memory:")
    yield database
    database.close()


# ------------------------------------------------------------------
# Customers
# ------------------------------------------------------------------
def test_add_and_list_customer(db):
    db.add_customer("Alice")
    customers = db.list_customers()
    assert len(customers) == 1
    assert customers[0].name == "Alice"


def test_update_customer(db):
    customer_id = db.add_customer("Alice")
    db.update_customer(customer_id, "Alicia")
    customers = db.list_customers()
    assert customers[0].name == "Alicia"


def test_delete_customer(db):
    customer_id = db.add_customer("Alice")
    db.delete_customer(customer_id)
    assert db.list_customers() == []


# ------------------------------------------------------------------
# Menu items
# ------------------------------------------------------------------
def test_add_and_list_menu_item(db):
    db.add_menu_item("Margherita", 8.5)
    items = db.list_menu_items()
    assert len(items) == 1
    assert items[0].name == "Margherita"
    assert items[0].price == 8.5


def test_update_menu_item(db):
    item_id = db.add_menu_item("Margherita", 8.5)
    db.update_menu_item(item_id, "Margherita XL", 11.0)
    items = db.list_menu_items()
    assert items[0].name == "Margherita XL"
    assert items[0].price == 11.0


def test_delete_menu_item(db):
    item_id = db.add_menu_item("Margherita", 8.5)
    db.delete_menu_item(item_id)
    assert db.list_menu_items() == []


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------
def test_add_and_list_order(db):
    customer_id = db.add_customer("Alice")
    item_id = db.add_menu_item("Margherita", 8.5)
    db.add_order(customer_id, item_id, 2)

    orders = db.list_orders()
    assert len(orders) == 1
    order = orders[0]
    assert order.customer_name == "Alice"
    assert order.menu_item_name == "Margherita"
    assert order.quantity == 2
    assert order.total == 17.0


def test_delete_order(db):
    customer_id = db.add_customer("Alice")
    item_id = db.add_menu_item("Margherita", 8.5)
    order_id = db.add_order(customer_id, item_id, 2)
    db.delete_order(order_id)
    assert db.list_orders() == []


def test_deleting_customer_cascades_to_orders(db):
    """Deleting a customer should also remove their past orders (ON DELETE CASCADE)."""
    customer_id = db.add_customer("Alice")
    item_id = db.add_menu_item("Margherita", 8.5)
    db.add_order(customer_id, item_id, 2)

    db.delete_customer(customer_id)

    assert db.list_orders() == []


def test_total_revenue(db):
    customer_id = db.add_customer("Alice")
    item_id = db.add_menu_item("Margherita", 10.0)
    db.add_order(customer_id, item_id, 3)  # 30.0
    db.add_order(customer_id, item_id, 2)  # 20.0

    assert db.total_revenue() == 50.0


def test_total_revenue_with_no_orders_is_zero(db):
    assert db.total_revenue() == 0


# ------------------------------------------------------------------
# Tables
# ------------------------------------------------------------------
def test_add_and_list_table(db):
    db.add_table(4, 6)
    tables = db.list_tables()
    assert len(tables) == 1
    assert tables[0].number == 4
    assert tables[0].capacity == 6


def test_update_table(db):
    table_id = db.add_table(4, 6)
    db.update_table(table_id, 4, 8)
    assert db.list_tables()[0].capacity == 8


def test_delete_table(db):
    table_id = db.add_table(4, 6)
    db.delete_table(table_id)
    assert db.list_tables() == []


def test_duplicate_table_number_raises(db):
    db.add_table(4, 6)
    with pytest.raises(Exception):
        db.add_table(4, 2)


# ------------------------------------------------------------------
# Reservations
# ------------------------------------------------------------------
def test_add_and_list_reservation(db):
    customer_id = db.add_customer("Alice")
    table_id = db.add_table(4, 6)
    db.add_reservation(table_id, customer_id, "25/12/2026", "19:30", 4)

    reservations = db.list_reservations()
    assert len(reservations) == 1
    reservation = reservations[0]
    assert reservation.table_number == 4
    assert reservation.customer_name == "Alice"
    assert reservation.guests == 4


def test_is_table_booked(db):
    customer_id = db.add_customer("Alice")
    table_id = db.add_table(4, 6)
    db.add_reservation(table_id, customer_id, "25/12/2026", "19:30", 4)

    assert db.is_table_booked(table_id, "25/12/2026", "19:30") is True
    assert db.is_table_booked(table_id, "25/12/2026", "20:00") is False


def test_delete_reservation(db):
    customer_id = db.add_customer("Alice")
    table_id = db.add_table(4, 6)
    reservation_id = db.add_reservation(table_id, customer_id, "25/12/2026", "19:30", 4)
    db.delete_reservation(reservation_id)
    assert db.list_reservations() == []


def test_deleting_table_cascades_to_reservations(db):
    customer_id = db.add_customer("Alice")
    table_id = db.add_table(4, 6)
    db.add_reservation(table_id, customer_id, "25/12/2026", "19:30", 4)

    db.delete_table(table_id)

    assert db.list_reservations() == []


# ------------------------------------------------------------------
# Orders linked to a reservation (pre-ordered food)
# ------------------------------------------------------------------
def test_order_linked_to_reservation(db):
    customer_id = db.add_customer("Alice")
    table_id = db.add_table(4, 6)
    item_id = db.add_menu_item("Margherita", 8.5)
    reservation_id = db.add_reservation(table_id, customer_id, "25/12/2026", "19:30", 4)

    db.add_order(customer_id, item_id, 2, reservation_id=reservation_id)

    linked_orders = db.list_orders_for_reservation(reservation_id)
    assert len(linked_orders) == 1
    assert linked_orders[0].reservation_id == reservation_id
    assert linked_orders[0].total == 17.0


def test_deleting_reservation_keeps_order_but_unlinks_it(db):
    """Food already ordered shouldn't vanish just because the booking was removed."""
    customer_id = db.add_customer("Alice")
    table_id = db.add_table(4, 6)
    item_id = db.add_menu_item("Margherita", 8.5)
    reservation_id = db.add_reservation(table_id, customer_id, "25/12/2026", "19:30", 4)
    db.add_order(customer_id, item_id, 2, reservation_id=reservation_id)

    db.delete_reservation(reservation_id)

    orders = db.list_orders()
    assert len(orders) == 1
    assert orders[0].reservation_id is None


# ------------------------------------------------------------------
# Customer phone numbers
# ------------------------------------------------------------------
def test_add_customer_with_phone_number(db):
    db.add_customer("Alice", "+242060000001")
    customer = db.list_customers()[0]
    assert customer.phone_number == "+242060000001"


def test_duplicate_phone_number_raises_value_error(db):
    db.add_customer("Alice", "+242060000001")
    with pytest.raises(ValueError):
        db.add_customer("Someone Else", "+242060000001")


def test_multiple_customers_without_phone_are_allowed(db):
    """NULL phone numbers shouldn't collide with each other."""
    db.add_customer("Alice")
    db.add_customer("Bob")
    assert len(db.list_customers()) == 2


def test_update_customer_to_duplicate_phone_raises(db):
    db.add_customer("Alice", "+242060000001")
    bob_id = db.add_customer("Bob", "+242060000002")
    with pytest.raises(ValueError):
        db.update_customer(bob_id, "Bob", "+242060000001")


# ------------------------------------------------------------------
# Menu item categories
# ------------------------------------------------------------------
def test_menu_item_defaults_to_food_category(db):
    db.add_menu_item("Margherita", 8.5)
    assert db.list_menu_items()[0].category == "Food"


def test_add_drink_menu_item(db):
    db.add_menu_item("Beer", 4.0, category="Drink")
    item = db.list_menu_items()[0]
    assert item.category == "Drink"


# ------------------------------------------------------------------
# Analysis: customer spending report (grouped by phone number)
# ------------------------------------------------------------------
def test_customer_spending_report(db):
    alice = db.add_customer("Alice", "+242060000001")
    bob = db.add_customer("Bob", "+242060000002")
    pizza = db.add_menu_item("Margherita", 10.0)

    db.add_order(alice, pizza, 3)  # 30.0
    db.add_order(alice, pizza, 1)  # 10.0 -> Alice: 2 orders, 4 items, 40.0
    db.add_order(bob, pizza, 1)    # 10.0 -> Bob: 1 order, 1 item, 10.0

    report = db.customer_spending_report()
    by_phone = {row.phone_number: row for row in report}

    assert by_phone["+242060000001"].order_count == 2
    assert by_phone["+242060000001"].items_count == 4
    assert by_phone["+242060000001"].total_spent == 40.0

    assert by_phone["+242060000002"].total_spent == 10.0

    # Sorted with the biggest spender first
    assert report[0].phone_number == "+242060000001"


def test_customer_spending_report_includes_customers_with_no_orders(db):
    db.add_customer("Alice", "+242060000001")
    report = db.customer_spending_report()
    assert len(report) == 1
    assert report[0].order_count == 0
    assert report[0].total_spent == 0


# ------------------------------------------------------------------
# Analysis: best-selling food / drinks
# ------------------------------------------------------------------
def test_top_selling_items_by_category(db):
    alice = db.add_customer("Alice")
    pizza = db.add_menu_item("Margherita", 10.0, category="Food")
    pasta = db.add_menu_item("Carbonara", 12.0, category="Food")
    beer = db.add_menu_item("Beer", 4.0, category="Drink")

    db.add_order(alice, pizza, 5)
    db.add_order(alice, pasta, 2)
    db.add_order(alice, beer, 10)

    top_food = db.top_selling_items(category="Food")
    assert top_food[0].name == "Margherita"
    assert top_food[0].quantity_sold == 5

    top_drinks = db.top_selling_items(category="Drink")
    assert top_drinks[0].name == "Beer"
    assert top_drinks[0].quantity_sold == 10


def test_top_selling_items_respects_limit(db):
    alice = db.add_customer("Alice")
    for i in range(5):
        item_id = db.add_menu_item(f"Item {i}", 1.0, category="Food")
        db.add_order(alice, item_id, i + 1)

    top_3 = db.top_selling_items(category="Food", limit=3)
    assert len(top_3) == 3
    # Highest quantity first
    assert top_3[0].quantity_sold == 5


# ------------------------------------------------------------------
# Revenue by time period
# ------------------------------------------------------------------
def test_revenue_today_and_this_week(db):
    alice = db.add_customer("Alice")
    item_id = db.add_menu_item("Pizza", 10.0)
    db.add_order(alice, item_id, 2)  # placed "now" -> counts as today and this week

    assert db.revenue_today() == 20.0
    assert db.revenue_this_week() == 20.0
    assert db.total_revenue() == 20.0


def test_daily_revenue_has_one_entry_per_day(db):
    alice = db.add_customer("Alice")
    item_id = db.add_menu_item("Pizza", 10.0)
    db.add_order(alice, item_id, 1)

    daily = db.daily_revenue(days=7)
    assert len(daily) == 7
    # Today's entry (last one) should reflect the order just placed
    assert daily[-1][1] == 10.0
    # Days with no orders show up as 0.0 rather than being skipped
    assert daily[0][1] == 0.0


# ------------------------------------------------------------------
# Customer segmentation (Regular vs Occasional)
# ------------------------------------------------------------------
def test_customer_segment_occasional_by_default(db):
    alice = db.add_customer("Alice", "+242060000001")
    item_id = db.add_menu_item("Pizza", 10.0)
    db.add_order(alice, item_id, 1)  # only 1 order

    report = db.customer_spending_report()
    assert report[0].segment == "Occasional"


def test_customer_segment_becomes_regular_past_threshold(db):
    from database import REGULAR_CUSTOMER_ORDER_THRESHOLD

    alice = db.add_customer("Alice", "+242060000001")
    item_id = db.add_menu_item("Pizza", 10.0)
    for _ in range(REGULAR_CUSTOMER_ORDER_THRESHOLD):
        db.add_order(alice, item_id, 1)

    report = db.customer_spending_report()
    assert report[0].segment == "Regular"
