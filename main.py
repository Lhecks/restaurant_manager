"""
main.py
--------
Entry point for the Restaurant Management app.

Run with:
    python main.py
"""

from ui import RestaurantApp

if __name__ == "__main__":
    app = RestaurantApp("restaurant.db")
    app.run()
