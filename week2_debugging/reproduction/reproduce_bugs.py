#!/usr/bin/env python3
"""Reproduce all 12 bugs in ../buggy_original.py - safely and on demand.

Every check prints [REPRODUCED], [NOT REPRODUCED] or [SKIPPED] and the
observed vs expected behaviour, so the output of this file is itself
evidence for the debugging log.  Nothing here modifies the original: the
buggy functions are imported and exercised with throwaway inputs.

Run from the project root:  python reproduction/reproduce_bugs.py
Exit code 0 means "every known bug reproduced" (i.e. the baseline still
behaves as documented in BUG_REPORT.md).
"""

from __future__ import annotations

import copy
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import buggy_original as buggy  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def report(bug_id: str, reproduced: bool, detail: str) -> None:
    RESULTS.append((bug_id, reproduced, detail))
    status = "REPRODUCED" if reproduced else "NOT REPRODUCED"
    print(f"[{status}] {bug_id}: {detail}")


def fresh_inventory() -> list[dict]:
    return [
        {"name": "Notebook", "price": 120.0, "quantity": 10, "tags": []},
        {"name": "Pen", "price": 20.0, "quantity": 3, "tags": []},
        {"name": "Backpack", "price": 899.0, "quantity": 5, "tags": []},
    ]


def bug_01_mutable_default() -> None:
    p1 = buggy.create_product("A", 10.0, 1)
    p1["tags"].append("sale")
    p2 = buggy.create_product("B", 20.0, 1)
    reproduced = "sale" in p2["tags"]
    report("BUG-01", reproduced,
           f"tag added to product A leaked into product B: B.tags={p2['tags']} "
           f"(expected [] - mutable default argument)")


def bug_02_off_by_one_total() -> None:
    inventory = fresh_inventory()
    expected = 120.0 * 10 + 20.0 * 3 + 899.0 * 5  # 5755.0
    observed = buggy.calculate_total_value(inventory)
    report("BUG-02", observed != expected,
           f"calculate_total_value -> {observed}, expected {expected} "
           f"(first product silently skipped, range starts at 1)")


def bug_03_average_empty() -> None:
    try:
        buggy.average_price([])
    except ZeroDivisionError as exc:
        report("BUG-03", True, f"average_price([]) crashed: ZeroDivisionError: {exc}")
        return
    report("BUG-03", False, "average_price([]) returned without crashing")


def bug_04_discount_logic() -> None:
    observed = buggy.apply_discount(100.0, 10)
    report("BUG-04", observed != 90.0,
           f"apply_discount(100, 10%) -> {observed}, expected 90.0 "
           f"(returns the discount amount, not the final price)")


def bug_05_csv_load() -> None:
    csv_path = Path(__file__).resolve().parents[1] / "data" / "sample_inventory.csv"
    try:
        loaded = buggy.load_inventory(str(csv_path))
    except Exception as exc:  # ValueError on the header row is the bug
        report("BUG-05", True,
               f"load_inventory(sample_inventory.csv) crashed: {type(exc).__name__}: {exc}")
        return
    types = [type(p["quantity"]).__name__ for p in loaded]
    report("BUG-05", any(t == "str" for t in types),
           f"load_inventory returned quantities as {types} (expected int)")


def bug_06_overselling() -> None:
    inventory = fresh_inventory()
    ok = buggy.sell_product(inventory, "Pen", 50)
    pen = inventory[1]
    report("BUG-06", bool(ok) and pen["quantity"] < 0,
           f"sold 50 Pens with only 3 in stock -> quantity is now {pen['quantity']} "
           f"(expected: sale rejected, stock stays 3)")


def bug_07_wrong_sorting() -> None:
    inventory = fresh_inventory() + [
        {"name": "Water Bottle", "price": 249.5, "quantity": 8, "tags": []}
    ]
    names = [p["name"] for p in buggy.most_expensive(inventory, 2)]
    expected = ["Backpack", "Water Bottle"]
    report("BUG-07", names != expected,
           f"most_expensive(2) -> {names}, expected {expected} "
           f"(ascending sort on str(price))")


def bug_08_shallow_backup() -> None:
    inventory = fresh_inventory()
    backup = buggy.backup_inventory(inventory)
    backup[0]["price"] = 1.0
    report("BUG-08", inventory[0]["price"] == 1.0,
           f"editing the 'backup' changed the live inventory too "
           f"(Notebook price is now {inventory[0]['price']}, expected 120.0)")


def bug_09_infinite_loop() -> None:
    inventory = fresh_inventory()  # Notebook qty 10 > threshold 3 -> `continue` path
    holder: dict = {}

    def target() -> None:
        holder["result"] = buggy.collect_restock_names(inventory, 3)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=1.0)
    reproduced = thread.is_alive()
    report("BUG-09", reproduced,
           "collect_restock_names(threshold=3) still running after 1.0s - "
           "infinite loop (`continue` before i += 1); daemon thread abandoned"
           if reproduced else
           f"collect_restock_names returned {holder.get('result')}")


def bug_10_wrong_key() -> None:
    try:
        buggy.inventory_summary(fresh_inventory())
    except KeyError as exc:
        report("BUG-10", True, f"inventory_summary crashed: KeyError: {exc} "
                                f"('qty' used instead of 'quantity')")
        return
    report("BUG-10", False, "inventory_summary returned without crashing")


def bug_11_global_counter() -> None:
    try:
        buggy.record_sale(120.0)
    except UnboundLocalError as exc:
        report("BUG-11", True, f"record_sale crashed: UnboundLocalError: {exc}")
        return
    report("BUG-11", False, "record_sale returned without crashing")


def bug_12_append_save() -> None:
    inventory = fresh_inventory()
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "saved.csv"
        buggy.save_inventory(inventory, str(path))
        first = path.read_text(encoding="utf-8") if path.exists() else ""
        buggy.save_inventory(inventory, str(path))
        second = path.read_text(encoding="utf-8") if path.exists() else ""
    report("BUG-12", second != first or second.count("name,price,quantity") > 1,
           f"file after 1st save = {len(first.splitlines())} lines, "
           f"after 2nd save = {len(second.splitlines())} lines "
           f"(expected: identical file; opened in append mode instead of write mode)")


CHECKS = [
    bug_01_mutable_default,
    bug_02_off_by_one_total,
    bug_03_average_empty,
    bug_04_discount_logic,
    bug_05_csv_load,
    bug_06_overselling,
    bug_07_wrong_sorting,
    bug_08_shallow_backup,
    bug_09_infinite_loop,
    bug_10_wrong_key,
    bug_11_global_counter,
    bug_12_append_save,
]


def main() -> int:
    print("Reproducing Week 2 bugs against buggy_original.py")
    print("=" * 72)
    snapshot = copy.deepcopy(buggy.SALES_COUNT)
    for check in CHECKS:
        try:
            check()
        except Exception as exc:  # a reproduction must never blow up the harness
            report(check.__name__, False, f"reproduction harness error: {type(exc).__name__}: {exc}")
    _ = snapshot
    print("=" * 72)
    reproduced = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"{reproduced}/{len(RESULTS)} bugs reproduced against the original script.")
    print("Now run the regression suite against the fixed version:")
    print("    python -m unittest discover -s tests -v")
    return 0 if reproduced == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
