"""Regression tests for the Week 2 debugging exercise.

One test class (or clearly named test) per bug: BUG-01 ... BUG-12, so a
failure message points straight back to BUG_REPORT.md.  Written with the
standard-library ``unittest`` so they run anywhere, and equally
discoverable by pytest.

    python -m unittest discover -s tests -v
    python -m pytest -q
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inventory_manager as fixed  # noqa: E402


def sample_inventory() -> list[dict]:
    return [
        fixed.create_product("Notebook", 120.0, 10),
        fixed.create_product("Pen", 20.0, 3),
        fixed.create_product("Backpack", 899.0, 5),
    ]


class BugRegressionTests(unittest.TestCase):
    """Every test in this class FAILS against buggy_original.py."""

    def setUp(self) -> None:
        fixed.SALES_COUNT = 0
        fixed.SALES_TOTAL = 0.0

    # ---- BUG-01 ------------------------------------------------------ #
    def test_bug01_products_do_not_share_a_default_tag_list(self) -> None:
        first = fixed.create_product("A", 10.0, 1)
        first["tags"].append("sale")
        second = fixed.create_product("B", 20.0, 1)
        self.assertEqual(second["tags"], [])
        self.assertIsNot(first["tags"], second["tags"])
        supplied = ["stationery"]
        third = fixed.create_product("C", 5.0, 1, tags=supplied)
        supplied.append("mutated later")
        self.assertEqual(third["tags"], ["stationery"])

    # ---- BUG-02 ------------------------------------------------------ #
    def test_bug02_total_value_includes_every_product(self) -> None:
        self.assertEqual(fixed.calculate_total_value(sample_inventory()), 5755.0)
        self.assertEqual(fixed.calculate_total_value(sample_inventory()[:1]), 1200.0)
        self.assertEqual(fixed.calculate_total_value([]), 0.0)

    # ---- BUG-03 ------------------------------------------------------ #
    def test_bug03_average_price_of_empty_inventory_is_zero(self) -> None:
        self.assertEqual(fixed.average_price([]), 0.0)
        self.assertAlmostEqual(fixed.average_price(sample_inventory()), 346.33)

    # ---- BUG-04 ------------------------------------------------------ #
    def test_bug04_discount_returns_the_final_price(self) -> None:
        self.assertEqual(fixed.apply_discount(100.0, 10), 90.0)
        self.assertEqual(fixed.apply_discount(899.0, 10), 809.1)
        self.assertEqual(fixed.apply_discount(50.0, 0), 50.0)
        self.assertEqual(fixed.apply_discount(50.0, 100), 0.0)

    # ---- BUG-05 ------------------------------------------------------ #
    def test_bug05_load_inventory_parses_header_and_types(self) -> None:
        csv_path = Path(__file__).resolve().parents[1] / "data" / "sample_inventory.csv"
        inventory = fixed.load_inventory(csv_path)
        self.assertEqual(len(inventory), 5)
        self.assertEqual(inventory[0]["name"], "Notebook")
        self.assertIsInstance(inventory[0]["price"], float)
        self.assertIsInstance(inventory[0]["quantity"], int)
        # ...and arithmetic that would explode on strings works:
        self.assertEqual(fixed.calculate_total_value(inventory), 9398.0)

    def test_bug05_load_inventory_reports_the_bad_line(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            path.write_text("name,price,quantity\nPen,not-a-price,3\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                fixed.load_inventory(path)
        self.assertIn("line 2", str(ctx.exception))

    # ---- BUG-06 ------------------------------------------------------ #
    def test_bug06_cannot_sell_more_than_is_in_stock(self) -> None:
        inventory = sample_inventory()
        with self.assertRaises(ValueError):
            fixed.sell_product(inventory, "Pen", 50)
        self.assertEqual(inventory[1]["quantity"], 3)  # untouched after rejection
        self.assertTrue(fixed.sell_product(inventory, "Pen", 3))
        self.assertEqual(inventory[1]["quantity"], 0)

    def test_bug06_invalid_sales_are_rejected_loudly(self) -> None:
        inventory = sample_inventory()
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                fixed.sell_product(inventory, "Pen", bad)
        with self.assertRaises(ValueError):
            fixed.sell_product(inventory, "Nonexistent", 1)
        with self.assertRaises(TypeError):
            fixed.sell_product(inventory, "Pen", 1.5)  # type: ignore[arg-type]

    # ---- BUG-07 ------------------------------------------------------ #
    def test_bug07_most_expensive_is_numeric_and_descending(self) -> None:
        inventory = sample_inventory() + [fixed.create_product("Water Bottle", 249.5, 8)]
        names = [p["name"] for p in fixed.most_expensive(inventory, 2)]
        self.assertEqual(names, ["Backpack", "Water Bottle"])
        prices = [p["price"] for p in fixed.most_expensive(inventory, 4)]
        self.assertEqual(prices, sorted(prices, reverse=True))

    # ---- BUG-08 ------------------------------------------------------ #
    def test_bug08_backup_is_a_deep_independent_copy(self) -> None:
        inventory = sample_inventory()
        backup = fixed.backup_inventory(inventory)
        backup[0]["price"] = 1.0
        backup[0]["tags"].append("tampered")
        backup.append(fixed.create_product("Extra", 1.0, 1))
        self.assertEqual(inventory[0]["price"], 120.0)
        self.assertEqual(inventory[0]["tags"], [])
        self.assertEqual(len(inventory), 3)

    # ---- BUG-09 ------------------------------------------------------ #
    def test_bug09_collect_restock_names_terminates(self) -> None:
        # Notebook (qty 10) sits above the threshold: the buggy while-loop
        # never finished on exactly this input.
        self.assertEqual(fixed.collect_restock_names(sample_inventory(), 3), ["Pen"])
        self.assertEqual(fixed.collect_restock_names(sample_inventory(), 10),
                         ["Notebook", "Pen", "Backpack"])
        self.assertEqual(fixed.collect_restock_names([], 5), [])

    # ---- BUG-10 ------------------------------------------------------ #
    def test_bug10_inventory_summary_uses_the_quantity_key(self) -> None:
        summary = fixed.inventory_summary(sample_inventory())
        self.assertEqual(summary["product_count"], 3)
        self.assertEqual(summary["total_items"], 18)
        self.assertEqual(summary["total_value"], 5755.0)

    # ---- BUG-11 ------------------------------------------------------ #
    def test_bug11_record_sale_updates_the_global_counter(self) -> None:
        self.assertEqual(fixed.record_sale(120.0), 1)
        self.assertEqual(fixed.record_sale(20.0), 2)
        self.assertEqual(fixed.SALES_TOTAL, 140.0)

    # ---- BUG-12 ------------------------------------------------------ #
    def test_bug12_saving_twice_produces_the_same_file(self) -> None:
        inventory = sample_inventory()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "saved.csv"
            fixed.save_inventory(inventory, path)
            first = path.read_bytes()
            fixed.save_inventory(inventory, path)
            second = path.read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(second.decode("utf-8").count("name,price,quantity"), 1)


class BehaviourTests(unittest.TestCase):
    """Behaviour the refactor promised to preserve (or explicitly added)."""

    def setUp(self) -> None:
        fixed.SALES_COUNT = 0
        fixed.SALES_TOTAL = 0.0

    def test_create_product_validation(self) -> None:
        with self.assertRaises(ValueError):
            fixed.create_product("  ", 10.0, 1)
        with self.assertRaises(ValueError):
            fixed.create_product("X", -5.0, 1)
        with self.assertRaises(ValueError):
            fixed.create_product("X", 5.0, -1)
        product = fixed.create_product("  Pen  ", 20, 3)
        self.assertEqual(product["name"], "Pen")  # trimmed
        self.assertEqual(product["price"], 20.0)

    def test_discount_bounds_are_enforced(self) -> None:
        for bad in (-5, 101):
            with self.assertRaises(ValueError):
                fixed.apply_discount(100.0, bad)

    def test_restock_product(self) -> None:
        inventory = sample_inventory()
        self.assertTrue(fixed.restock_product(inventory, "Pen", 7))
        self.assertEqual(inventory[1]["quantity"], 10)
        with self.assertRaises(ValueError):
            fixed.restock_product(inventory, "Ghost", 1)

    def test_csv_round_trip(self) -> None:
        inventory = sample_inventory()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "round_trip.csv"
            fixed.save_inventory(inventory, path)
            reloaded = fixed.load_inventory(path)
        expected = [
            {"name": p["name"], "price": p["price"], "quantity": p["quantity"]} for p in inventory
        ]
        actual = [
            {"name": p["name"], "price": p["price"], "quantity": p["quantity"]} for p in reloaded
        ]
        self.assertEqual(actual, expected)

    def test_missing_csv_file_is_a_clear_error(self) -> None:
        with self.assertRaises(FileNotFoundError):
            fixed.load_inventory("/nonexistent/definitely_missing.csv")

    def test_search_helpers(self) -> None:
        inventory = sample_inventory()
        self.assertEqual(fixed.search_product(inventory, "Pen")["name"], "Pen")
        self.assertIsNone(fixed.search_product(inventory, "ghost"))
        hits = fixed.search_products(inventory, "NOTE")
        self.assertEqual([p["name"] for p in hits], ["Notebook"])
        with self.assertRaises(ValueError):
            fixed.search_products(inventory, "   ")

    def test_most_expensive_edge_cases(self) -> None:
        self.assertEqual(fixed.most_expensive(sample_inventory(), 0), [])
        self.assertEqual(len(fixed.most_expensive(sample_inventory(), 99)), 3)
        with self.assertRaises(ValueError):
            fixed.most_expensive(sample_inventory(), -1)

    def test_main_demo_runs_cleanly(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = fixed.main([])
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Total inventory value: 5755.0", text)
        self.assertIn("Backpack after 10% discount: 809.1", text)
        self.assertIn("Sales so far: 1", text)


if __name__ == "__main__":
    unittest.main()
