# Bug Report — Week 2: Debugging and Troubleshooting

**Script under investigation:** `buggy_original.py` (163 lines, 15 functions) — preserved unmodified
**Corrected script:** `inventory_manager.py` (same public API, 351 lines incl. documentation)
**Environment:** Python 3.13, standard library only
**Reproduction:** `python reproduction/reproduce_bugs.py` → **12/12 bugs reproduced**
**Verification:** `python -m unittest discover -s tests -v` → **22 tests, all passing**

---

## 1. Summary of all defects

| ID | Severity | Category | Location (original) | Symptom / Evidence | Root Cause |
|---|---|---|---|---|---|
| BUG-01 | Medium | Python semantics | `create_product`, line 29 | Tag added to one product appears on products created later | Mutable default argument `tags=[]` shared by every call |
| BUG-02 | High | Loop / off-by-one | `calculate_total_value`, line 41 | Total is **4555.0** instead of **5755.0** | `range(1, len(...))` skips index 0, the first product |
| BUG-03 | Medium | Runtime exception | `average_price`, line 50 | `ZeroDivisionError: division by zero` on an empty inventory | Unconditional division by `len(inventory)` |
| BUG-04 | High | Logic (silent wrong result) | `apply_discount`, lines 54–56 | 10% off Rs. 100 returns **10.0**, and off Rs. 899 returns **89.9** | Returns the discount *amount*, not the final price |
| BUG-05 | **Critical** | File I/O / parsing | `load_inventory`, lines 59–72 | `ValueError: could not convert string to float: 'price'` on any valid CSV | Header row parsed as data; manual `split(",")`; `quantity` left as `str`; file never closed |
| BUG-06 | **Critical** | Validation / business rule | `sell_product`, lines 83–93 | Selling 50 pens from a stock of 3 succeeds → quantity **−47** | No check that requested quantity ≤ stock on hand |
| BUG-07 | Medium | Logic / sorting | `most_expensive`, lines 103–105 | “Most expensive 2” returns `['Notebook', 'Pen']` | Sorts *ascending* by `str(price)` and takes the first n |
| BUG-08 | High | Python semantics / aliasing | `backup_inventory`, lines 108–110 | Editing the “backup” also changes the live inventory | `inventory[:]` is a shallow copy — inner dicts are shared |
| BUG-09 | **Critical** | Loop (hang) | `collect_restock_names`, lines 113–121 | Never returns when any product is above the threshold | `continue` executes before `i = i + 1` → infinite loop |
| BUG-10 | **Critical** | Runtime exception | `inventory_summary`, line 127 | `KeyError: 'qty'` — also crashes `main()` | Sums `product["qty"]`; the canonical key everywhere else is `"quantity"` |
| BUG-11 | High | Runtime exception / scope | `record_sale`, lines 136–138 | `UnboundLocalError: cannot access local variable 'SALES_COUNT'` | Assigns to a module global without a `global` declaration |
| BUG-12 | High | File I/O | `save_inventory`, lines 76–81 | File grows 4 → 8 → 12 lines; header repeated on every save | Opened in append mode (`"a"`), handle never closed |

**Severity key** — Critical: crash, hang, data/business-rule corruption. High: silently wrong money, stock, backup or saved data. Medium: wrong report or crash only in an edge case.

## 2. Defect profile

| Category | Bugs | Count |
|---|---|---|
| Silent wrong result (no exception) | BUG-01, 02, 04, 07, 08, 12 | 6 |
| Crash (exception raised) | BUG-03, 05, 10, 11 | 4 |
| Business-rule violation | BUG-06 | 1 |
| Hang (non-termination) | BUG-09 | 1 |

The most instructive finding of this exercise: **half of the defects never raise an
exception.** They were found only by comparing outputs against hand-computed expected
values, which is why every fix is locked in with a regression test rather than by
“the crash went away”.

## 3. Initial code-review hot spots (before running anything)

The brief asks for suspicious areas to be identified by reading first. These were
flagged on the first pass, and every one of them turned out to contain a real bug:

| Hot spot | Why it looked suspicious | Confirmed bug(s) |
|---|---|---|
| `create_product(..., tags=[])` | Classic mutable-default trap | BUG-01 |
| Manual CSV parsing + manual `open()` | Header handling, types, unclosed files, no `csv` module | BUG-05, BUG-12 |
| Index-based loops (`range(1, ...)`, `while i < len`) | Off-by-one and non-termination risks | BUG-02, BUG-09 |
| Arithmetic with no guard (`total / len(...)`) | Empty-collection edge case | BUG-03 |
| Money maths in one unexplained expression | Amount-vs-final-price confusion | BUG-04 |
| `sell_product` validates the *request* but not *stock* | Conditional checks the wrong variable | BUG-06 |
| `sorted(..., key=lambda p: str(p["price"]))` | Why convert a number to a string to sort it? | BUG-07 |
| `backup = inventory[:]` | Shallow copy presented as a backup | BUG-08 |
| Two spellings for one field (`qty` vs `quantity`) | Inconsistent naming across functions | BUG-10 |
| Module-level counter mutated inside a function | Missing `global` is a frequent beginner error | BUG-11 |

## 4. Status

All 12 defects are **fixed, regression-tested and documented** in
[`DEBUGGING_LOG.md`](DEBUGGING_LOG.md), which contains for each bug: the reproduction,
the observed-vs-expected behaviour, the hypothesis and the `pdb`/inspection evidence,
the root cause, before-and-after code, and the verifying test name.
