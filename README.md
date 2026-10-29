# Week 2 — Debugging and Troubleshooting Python Applications

**Internship:** Junior Python Developer · **Task:** Week 2 of 6
**Deliverable:** a corrected, bug-free Python script plus a comprehensive
debugging log documenting every defect, the diagnosis process and the fixes.

The subject script is a small shop **inventory manager**
(`buggy_original.py`, 163 lines). It contained **12 defects** — four crashes,
one infinite loop, one business-rule violation and six silent wrong results
spanning file I/O, loops, conditionals, sorting, copying and scope. All 12
are reproduced, diagnosed (including a real `pdb` session), fixed and
covered by named regression tests.

No third-party packages are required: **Python 3.9+ standard library only**.

---

## 1. Quick start

```bash
# 1. See every bug in the original, safely reproduced
python reproduction/reproduce_bugs.py        # -> 12/12 bugs reproduced

# 2. Run the corrected script
python inventory_manager.py                              # built-in demo data
python inventory_manager.py data/sample_inventory.csv    # report from a CSV file

# 3. Prove the fixes
python -m unittest discover -s tests -v      # 22 tests (or: python -m pytest -q)

# 4. (Optional) watch the original crash, exactly as first received
python buggy_original.py                     # KeyError: 'qty'
```

Expected headline results from the fixed version (all hand-verifiable):

```
Total inventory value: 5755.0        # buggy version printed 4555.0
Backpack after 10% discount: 809.1   # buggy version printed 89.9
Summary: {'product_count': 3, 'total_items': 18, 'total_value': 5755.0}
```

## 2. Project structure

```
week2_debugging/
├── buggy_original.py              # the script AS RECEIVED - preserved, do not fix
├── inventory_manager.py           # CORRECTED + refactored script (same public API)
├── BUG_REPORT.md                  # all 12 defects: severity, evidence, root cause
├── DEBUGGING_LOG.md               # full process log: method, pdb evidence,
│                                  # before/after code for every bug, lessons
├── README.md                      # this file
├── SUBMISSION_DESCRIPTION.txt     # 200+ word text for the submission portal
├── requirements.txt               # documents the (zero) runtime dependencies
├── reproduction/
│   └── reproduce_bugs.py          # runs all 12 reproductions, prints evidence
├── tests/
│   └── test_inventory_manager.py  # 22 tests; one named regression test per bug
├── docs/
│   └── pdb_session.txt            # real python -m pdb transcript (BUG-02, BUG-10)
└── data/
    └── sample_inventory.csv       # sample input used by the demo and tests
```

## 3. The 12 bugs at a glance

| ID | Defect | Symptom |
|---|---|---|
| BUG-01 | Mutable default `tags=[]` | Tags leak between unrelated products |
| BUG-02 | `range(1, ...)` off-by-one | Inventory total misses the first product (4555 vs 5755) |
| BUG-03 | Division by `len()` unguarded | `ZeroDivisionError` on an empty inventory |
| BUG-04 | Discount arithmetic inverted | Returns the saving (10.0), not the final price (90.0) |
| BUG-05 | Hand-rolled CSV parsing | Header row crashes `float('price')`; quantity left as `str` |
| BUG-06 | No stock-level check | Selling 50 of 3 pens “succeeds”, stock becomes −47 |
| BUG-07 | Sort by `str(price)`, ascending | “Most expensive” returns the cheapest items |
| BUG-08 | Shallow-copy “backup” | Editing the backup corrupts the live inventory |
| BUG-09 | `continue` before counter increment | Restock report loops forever |
| BUG-10 | `product["qty"]` vs `"quantity"` | `KeyError` crashes the summary and `main()` |
| BUG-11 | Missing `global` declaration | `UnboundLocalError` in the sales counter |
| BUG-12 | CSV opened in append mode | Every save duplicates the file, header included |

Full analysis, reproduction steps, hypotheses, `pdb` evidence and
before/after code for each: **[`DEBUGGING_LOG.md`](DEBUGGING_LOG.md)**.
Severity/category table and the initial code-review notes:
**[`BUG_REPORT.md`](BUG_REPORT.md)**.

## 4. Debugging method (summary)

For every defect: **reproduce → record observed vs expected → hypothesise →
inspect with `pdb`/REPL → fix minimally → add a regression test named after
the bug ID**. Fixes were completed and green before any refactoring, and the
refactor (single lookup helper, generators instead of index loops, the `csv`
module, type hints, rounded money values, validate-then-mutate) deliberately
preserved every public function name and the CSV format — the brief requires
better code *without* altered functionality.

Useful commands while exploring:

```bash
python -m pdb buggy_original.py     # step through the original yourself
diff -u buggy_original.py inventory_manager.py | less   # review every change
```

## 5. Testing

* **Reproduction harness** (`reproduction/reproduce_bugs.py`) — proves the
  baseline still exhibits all 12 defects; the infinite loop is demonstrated
  safely via a daemon thread with a 1-second timeout.
* **Regression suite** (`tests/test_inventory_manager.py`) — 22 `unittest`
  tests (pytest-compatible): 14 bug-named regressions plus behaviour tests
  (CSV round-trip, validation bounds, demo entry point, search). Every test
  in `BugRegressionTests` fails against the original script.

```bash
python -m unittest discover -s tests -v
# Ran 22 tests ... OK
```

## 6. Requirements

| Requirement | Value |
|---|---|
| Python | 3.9 or newer |
| Third-party dependencies | **None** |
| Optional | `pytest` as an alternative test runner |

## 7. Author

Week 2 deliverable for the Junior Python Developer internship
(14-Oct-2026 → 25-Nov-2026). Companion to the Week 1 CLI To-Do List Manager.
