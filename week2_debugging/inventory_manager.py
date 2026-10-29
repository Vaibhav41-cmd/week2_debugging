"""inventory_manager.py - small shop inventory manager (CORRECTED, Week 2).

This is the debugged and refactored version of ``buggy_original.py``.  The
public function names and the product-dict format are unchanged on purpose:
the task requires fixing defects and improving code quality *without
altering the intended functionality*, and an unchanged API makes every fix
directly diff-able against the original (comments below cite the bug IDs
from BUG_REPORT.md / DEBUGGING_LOG.md).

Usage:
    python inventory_manager.py                       # built-in demo data
    python inventory_manager.py data/sample_inventory.csv
"""

from __future__ import annotations

import argparse
import copy
import csv
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

Product = dict[str, Any]
Inventory = list[Product]

SALES_COUNT = 0
SALES_TOTAL = 0.0
CSV_FIELDS = ("name", "price", "quantity")


# --------------------------------------------------------------------- #
# Helpers (refactoring: sell/restock/search used to re-implement the
# same name-lookup loop three times - it now exists exactly once)
# --------------------------------------------------------------------- #
def _find_product(inventory: Iterable[Product], name: str) -> Optional[Product]:
    """Return the product called *name*, or None if there is no such product."""
    for product in inventory:
        if product["name"] == name:
            return product
    return None


def _require_product(inventory: Iterable[Product], name: str) -> Product:
    """Like :func:`_find_product` but raise a clear error when missing.

    The original silently returned False for an unknown product, which made
    a typo in a product name indistinguishable from a successful no-op.
    """
    product = _find_product(inventory, name)
    if product is None:
        raise ValueError(f"Product not found: {name!r}")
    return product


def _validate_quantity(quantity: int, *, allow_zero: bool = False) -> None:
    """Reject non-integer, negative (and, by default, zero) quantities."""
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise TypeError(f"quantity must be an int, got {type(quantity).__name__}")
    if quantity < 0 or (quantity == 0 and not allow_zero):
        raise ValueError(f"quantity must be positive, got {quantity}")


# --------------------------------------------------------------------- #
# Product creation  (fixes BUG-01)
# --------------------------------------------------------------------- #
def create_product(
    name: str,
    price: float,
    quantity: int,
    tags: Optional[Sequence[str]] = None,
) -> Product:
    """Create one product dict.

    Fix BUG-01: the original signature was ``tags=[]``.  Python evaluates a
    default argument once, so every product created without tags shared
    *the same list object* - tagging one product tagged them all.  The
    default is now ``None`` and each product gets its own fresh list; a
    caller-supplied sequence is copied for the same reason.
    """
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Product name must not be empty.")
    if price < 0:
        raise ValueError(f"Price must not be negative, got {price}.")
    _validate_quantity(quantity, allow_zero=True)
    return {
        "name": clean_name,
        "price": round(float(price), 2),
        "quantity": int(quantity),
        "tags": list(tags) if tags is not None else [],
    }


# --------------------------------------------------------------------- #
# Calculations  (fixes BUG-02, BUG-03, BUG-04)
# --------------------------------------------------------------------- #
def calculate_total_value(inventory: Iterable[Product]) -> float:
    """Total stock value: sum of ``price * quantity`` over *all* products.

    Fix BUG-02: the original loop was ``range(1, len(inventory))`` and
    silently skipped the first product (Rs. 4,555 instead of Rs. 5,755 on
    the demo data).  Iterating the items directly removes the index - and
    the whole class of off-by-one mistakes - entirely.
    """
    return round(sum(p["price"] * p["quantity"] for p in inventory), 2)


def average_price(inventory: Sequence[Product]) -> float:
    """Mean unit price, or 0.0 for an empty inventory.

    Fix BUG-03: the original divided by ``len(inventory)`` unconditionally
    and crashed with ZeroDivisionError on an empty list.  An empty shop is
    a legitimate state, not an error, so it now returns 0.0 (documented
    here and locked in by a regression test).
    """
    if not inventory:
        return 0.0
    return round(sum(p["price"] for p in inventory) / len(inventory), 2)


def apply_discount(price: float, discount_percent: float) -> float:
    """Return the FINAL price after a percentage discount.

    Fix BUG-04: the original returned ``price * discount_percent / 100``,
    which is the discount *amount* (Rs. 10 on a Rs. 100 item at 10%) rather
    than the payable price (Rs. 90).  A pure logic error - no exception,
    just confidently wrong money.
    """
    if price < 0:
        raise ValueError(f"Price must not be negative, got {price}.")
    if not 0 <= discount_percent <= 100:
        raise ValueError(
            f"discount_percent must be between 0 and 100, got {discount_percent}."
        )
    return round(price * (1 - discount_percent / 100), 2)


# --------------------------------------------------------------------- #
# File I/O  (fixes BUG-05, BUG-12)
# --------------------------------------------------------------------- #
def load_inventory(path: str | Path) -> Inventory:
    """Load products from a ``name,price,quantity`` CSV file.

    Fix BUG-05: the original split raw lines by hand, *including the
    header row*, so ``float("price")`` raised ValueError on the very first
    line - and had it got further, quantity would have stayed a string and
    blown up later in arithmetic.  Using ``csv.DictReader`` consumes the
    header properly, handles quoted commas, and each value is converted
    to its real type with the line number in any error message.  The file
    is opened with a context manager, explicit ``newline=""`` and UTF-8
    encoding (the csv module's documented requirements).
    """
    csv_path = Path(path)
    inventory: Inventory = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or [f.strip() for f in reader.fieldnames] != list(CSV_FIELDS):
            raise ValueError(
                f"{csv_path}: expected header {','.join(CSV_FIELDS)}, "
                f"got {reader.fieldnames!r}"
            )
        for line_number, row in enumerate(reader, start=2):  # line 1 is the header
            if not row or not (row.get("name") or "").strip():
                continue  # tolerate blank lines at end of file
            try:
                inventory.append(
                    create_product(
                        name=row["name"],
                        price=float(row["price"]),
                        quantity=int(row["quantity"]),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{csv_path} line {line_number}: invalid row {row!r} ({exc})"
                ) from exc
    return inventory


def save_inventory(inventory: Iterable[Product], path: str | Path) -> None:
    """Write the inventory CSV, replacing any previous contents.

    Fix BUG-12: the original opened the file in append mode (``"a"``) and
    never closed it, so every save duplicated the whole file (header
    included).  ``"w"`` + ``csv.DictWriter`` + a context manager make
    saving idempotent: saving twice produces exactly the same bytes as
    saving once, and the handle is always closed even on error.
    """
    csv_path = Path(path)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for product in inventory:
            writer.writerow({field: product[field] for field in CSV_FIELDS})


# --------------------------------------------------------------------- #
# Stock movements  (fixes BUG-06)
# --------------------------------------------------------------------- #
def sell_product(inventory: Inventory, name: str, quantity: int) -> bool:
    """Sell *quantity* units of *name*; return True on success.

    Fix BUG-06: the original only rejected a negative *requested*
    quantity and never compared it with the stock on hand, so selling 50
    pens out of a stock of 3 happily produced a quantity of -47.
    Insufficient stock and unknown products are now loud ValueErrors and
    the inventory is left untouched (validate first, mutate last).
    """
    _validate_quantity(quantity)
    product = _require_product(inventory, name)
    if quantity > product["quantity"]:
        raise ValueError(
            f"Cannot sell {quantity} x {name!r}: only {product['quantity']} in stock."
        )
    product["quantity"] -= quantity
    return True


def restock_product(inventory: Inventory, name: str, quantity: int) -> bool:
    """Add *quantity* units of *name* back into stock."""
    _validate_quantity(quantity)
    product = _require_product(inventory, name)
    product["quantity"] += quantity
    return True


# --------------------------------------------------------------------- #
# Reporting helpers  (fixes BUG-07, BUG-09, BUG-10)
# --------------------------------------------------------------------- #
def most_expensive(inventory: Iterable[Product], n: int) -> Inventory:
    """Return the *n* highest-priced products, most expensive first.

    Fix BUG-07: the original sorted ascending by ``str(price)`` and took
    the first n - two mistakes in one line (lexicographic ordering makes
    "120.0" < "20.0" < "899.0", and ascending returns the *cheapest*).
    Prices are numbers: sort numerically with ``reverse=True``.
    """
    if n < 0:
        raise ValueError(f"n must not be negative, got {n}.")
    return sorted(inventory, key=lambda p: p["price"], reverse=True)[:n]


def collect_restock_names(inventory: Iterable[Product], threshold: int) -> list[str]:
    """Names of products at or below the reorder *threshold*.

    Fix BUG-09: the original used a manual ``while`` loop whose
    ``continue`` branch skipped the ``i = i + 1`` increment, so the first
    well-stocked product hung the program forever.  A list comprehension
    has no index to forget, terminates by construction, and says what it
    does in one line.
    """
    return [p["name"] for p in inventory if p["quantity"] <= threshold]


def inventory_summary(inventory: Sequence[Product]) -> dict[str, Any]:
    """Headline numbers for a report: product count, units, total value.

    Fix BUG-10: the original summed ``product["qty"]`` while every other
    function (and the data itself) uses ``"quantity"`` - an instant
    KeyError.  One canonical key name, used everywhere.
    """
    return {
        "product_count": len(inventory),
        "total_items": sum(p["quantity"] for p in inventory),
        "total_value": calculate_total_value(inventory),
    }


# --------------------------------------------------------------------- #
# Backup & sales counter  (fixes BUG-08, BUG-11)
# --------------------------------------------------------------------- #
def backup_inventory(inventory: Inventory) -> Inventory:
    """Return a fully independent copy of the inventory.

    Fix BUG-08: ``inventory[:]`` copies only the outer list; the product
    dicts inside are still the same objects, so editing the "backup"
    edited the live data.  ``copy.deepcopy`` duplicates the dicts (and
    their tag lists) too, which is what a backup means.
    """
    return copy.deepcopy(list(inventory))


def record_sale(amount: float) -> int:
    """Record one sale and return how many sales have been recorded.

    Fix BUG-11: the original incremented ``SALES_COUNT`` without declaring
    it ``global``, so Python treated it as a local and raised
    UnboundLocalError on first use.  (A class would be cleaner still, but
    the minimal correct fix keeps the module-level API unchanged; see
    DEBUGGING_LOG.md §7.)
    """
    global SALES_COUNT, SALES_TOTAL
    if amount < 0:
        raise ValueError(f"Sale amount must not be negative, got {amount}.")
    SALES_COUNT += 1
    SALES_TOTAL = round(SALES_TOTAL + float(amount), 2)
    return SALES_COUNT


# --------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------- #
def search_product(inventory: Iterable[Product], name: str) -> Optional[Product]:
    """Exact-name lookup (original API, now implemented via the helper)."""
    return _find_product(inventory, name)


def search_products(inventory: Iterable[Product], keyword: str) -> Inventory:
    """Case-insensitive partial-name search (small quality-of-life addition)."""
    needle = keyword.strip().lower()
    if not needle:
        raise ValueError("Search keyword must not be empty.")
    return [p for p in inventory if needle in p["name"].lower()]


# --------------------------------------------------------------------- #
# Demo / entry point
# --------------------------------------------------------------------- #
def _demo_inventory() -> Inventory:
    return [
        create_product("Notebook", 120.0, 10),
        create_product("Pen", 20.0, 3),
        create_product("Backpack", 899.0, 5),
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Print a short, correct inventory report (mirrors the buggy demo)."""
    parser = argparse.ArgumentParser(description="Small shop inventory report (Week 2, fixed).")
    parser.add_argument("csv_file", nargs="?", help="optional name,price,quantity CSV file")
    args = parser.parse_args(argv)

    inventory = load_inventory(args.csv_file) if args.csv_file else _demo_inventory()

    print("Products:")
    for product in inventory:
        print(f"  - {product['name']}: price={product['price']:.2f} quantity={product['quantity']}")
    print("Total inventory value:", calculate_total_value(inventory))
    print("Average price:", average_price(inventory))
    if inventory:
        top = most_expensive(inventory, 1)[0]
        print(f"Most expensive: {top['name']} ({top['price']:.2f})")
        print(f"{top['name']} after 10% discount:", apply_discount(top["price"], 10))
    print("Summary:", inventory_summary(inventory))
    print("Restock (<=3):", collect_restock_names(inventory, 3))
    print("Sales so far:", record_sale(120.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
