# Debugging Log — Week 2: Debugging and Troubleshooting Python Applications

**Goal:** take a defective Python script, reproduce and diagnose every problem
systematically, produce a corrected script that preserves the intended
functionality, and leave behind evidence (this log, a bug report, a
reproduction harness and regression tests) that the process was rigorous
rather than trial-and-error.

| Item | Value |
|---|---|
| Original script | `buggy_original.py` — 163 lines, 15 functions, preserved unmodified |
| Corrected script | `inventory_manager.py` — same public API, 351 lines incl. docstrings |
| Defects found | **12** (4 critical, 5 high, 3 medium) — see `BUG_REPORT.md` |
| Reproduction harness | `reproduction/reproduce_bugs.py` → **12/12 reproduced** |
| Regression suite | `tests/test_inventory_manager.py` → **22 tests, all passing** |
| Debugger evidence | `docs/pdb_session.txt` (real `python -m pdb` transcript) |
| Tools used | traceback analysis, `pdb` (breakpoints + post-mortem), REPL experiments, `timeout`/daemon-thread hang detection, `diff`, `unittest`/`pytest` |

---

## 1. Method: the loop applied to every bug

No fix was attempted before a bug could be reproduced on demand. Each defect
went through the same six steps, and the per-bug entries in §5 follow them:

1. **Reproduce** — the smallest input that triggers the symptom, kept in
   `reproduce_bugs.py` so it can be re-run forever.
2. **Observe vs. expect** — write down the actual output/exception *and* the
   hand-computed expected result. (Half of these bugs never raise, so
   “expected” had to come from arithmetic and the docstrings, not vibes.)
3. **Hypothesise** — one sentence naming the suspected mechanism.
4. **Inspect** — confirm or refute with `pdb`, a REPL probe or a targeted
   print, instead of editing on a guess.
5. **Fix minimally** — change only what the root cause requires; keep the
   function name, signature and data format intact.
6. **Lock it in** — a regression test named after the bug ID, plus a re-run
   of the whole suite to prove nothing else moved.

Only after all 12 were fixed did refactoring (§7) happen, as a separate step
with the tests as a safety net — fixes and clean-ups are never mixed
silently.

## 2. Tooling notes (what was actually used)

| Tool | How it earned its place |
|---|---|
| **Reading tracebacks bottom-up** | The last frame names the failing line; the frames above show the call path. Solved BUG-10 and BUG-05 in minutes. |
| **`python -m pdb script.py`** | Breakpoints (`break calculate_total_value`), stepping (`step`/`next`), inspecting (`p`, `args`, `list(product.keys())`), stack (`where`). Decisive for BUG-02. |
| **Post-mortem debugging** | `pdb` drops into the crashing frame on an uncaught exception; used to prove `product` had no `qty` key (BUG-10). |
| **REPL one-liners** | `sorted([...], key=str)` experiments (BUG-07), identity checks `a["tags"] is b["tags"]` (BUG-01), `copy` semantics (BUG-08). |
| **Daemon thread + `join(timeout=1.0)`** | Proves non-termination (BUG-09) without hanging the reproduction harness itself. |
| **`timeout 10 python buggy_original.py`** | Safe way to run code you suspect of looping forever. |
| **`diff -u buggy_original.py inventory_manager.py`** | Reviewing the final change set line by line before calling it done. |
| **`unittest` (and pytest)** | 22 regression tests; every bug has a test named after its ID. |

### 2.1 Real `pdb` session (excerpt of `docs/pdb_session.txt`)

A breakpoint inside `calculate_total_value` shows the loop variable starting
at **1** while the first product sits at index 0 — BUG-02 proven, not guessed.
Continuing then crashes in `inventory_summary`, and post-mortem inspection
shows the product's actual keys — BUG-10 proven the same way:

```
(Pdb) break calculate_total_value
(Pdb) continue
> buggy_original.py(40)calculate_total_value()
-> total = 0
(Pdb) step                      -> for i in range(1, len(inventory)):
(Pdb) step                      -> total = total + inventory[i]["price"] * inventory[i]["quantity"]
(Pdb) p i
1
(Pdb) p list(range(1, len(inventory)))
[1, 2]
(Pdb) p inventory[0]
{'name': 'Notebook', 'price': 120.0, 'quantity': 10, 'tags': []}
(Pdb) continue
...
KeyError: 'qty'
Uncaught exception. Entering post mortem debugging
> buggy_original.py(127)inventory_summary()
-> total_items = total_items + product["qty"]
(Pdb) p product
{'name': 'Notebook', 'price': 120.0, 'quantity': 10, 'tags': []}
(Pdb) p list(product.keys())
['name', 'price', 'quantity', 'tags']
```

## 3. Session timeline

| Session | Focus | Outcome |
|---|---|---|
| 1 — Code review | Read the script top to bottom; flag hot spots (file I/O, index loops, conditionals, globals, mutable defaults) | 10 suspicious areas logged in `BUG_REPORT.md` §3 |
| 2 — First run + tracebacks | `python buggy_original.py`, then each public function from the REPL | Main crashes (BUG-10); totals and discount visibly wrong (BUG-02/04) |
| 3 — Reproduction harness | Turn every suspicion into a runnable check; add safe hang detection | 12/12 reproduced with observed-vs-expected evidence |
| 4 — `pdb` deep dives | Breakpoints for the silent wrong-result bugs; post-mortem for the crashes | Root causes confirmed for BUG-02/07/09/10, transcript saved |
| 5 — Fixes + regression tests | One bug at a time: fix, run its reproduction against the fix, add the named test | 14 bug-named regression tests green |
| 6 — Refactor + final verification | Extract helpers, type hints, `csv` module, docstrings; full suite + fresh-run + `diff` review | 22/22 tests pass; original still reproduces 12/12 |

## 4. Starting evidence (before any fix)

```
$ python buggy_original.py
Total inventory value: 4555.0            <- expected 5755.0   (BUG-02)
Average price: 346.3333333333333
Backpack after 10% discount: 89.9        <- expected 809.1    (BUG-04)
Traceback (most recent call last):
  File "buggy_original.py", line 158, in main
    print("Summary:", inventory_summary(inventory))
  File "buggy_original.py", line 127, in inventory_summary
    total_items = total_items + product["qty"]
KeyError: 'qty'                          <- main never finishes (BUG-10)
```

```
$ python reproduction/reproduce_bugs.py
[REPRODUCED] BUG-01: tag added to product A leaked into product B: B.tags=['sale']
[REPRODUCED] BUG-02: calculate_total_value -> 4555.0, expected 5755.0
[REPRODUCED] BUG-03: average_price([]) crashed: ZeroDivisionError
[REPRODUCED] BUG-04: apply_discount(100, 10%) -> 10.0, expected 90.0
[REPRODUCED] BUG-05: load_inventory crashed: ValueError: could not convert ... 'price'
[REPRODUCED] BUG-06: sold 50 Pens with only 3 in stock -> quantity is now -47
[REPRODUCED] BUG-07: most_expensive(2) -> ['Notebook', 'Pen'], expected ['Backpack', 'Water Bottle']
[REPRODUCED] BUG-08: editing the 'backup' changed the live inventory too
[REPRODUCED] BUG-09: collect_restock_names still running after 1.0s - infinite loop
[REPRODUCED] BUG-10: inventory_summary crashed: KeyError: 'qty'
[REPRODUCED] BUG-11: record_sale crashed: UnboundLocalError: ... 'SALES_COUNT'
[REPRODUCED] BUG-12: file after 1st save = 4 lines, after 2nd save = 8 lines
12/12 bugs reproduced against the original script.
```

---

## 5. Bug-by-bug record

### BUG-01 — Tags leak between products (mutable default argument)

* **Observed:** `p1["tags"].append("sale")` makes a later product `p2` start
  life with `tags == ['sale']`. **Expected:** each product has independent tags.
* **Hypothesis:** the `tags=[]` default is one list object shared by all calls.
* **Inspection (REPL):** `p1["tags"] is p2["tags"]` → `True`. Confirmed: Python
  evaluates default arguments once, at function-definition time.

```python
# before
def create_product(name, price, quantity, tags=[]):
    product = {"name": name, "price": price, "quantity": quantity, "tags": tags}
    return product
```
```python
# after
def create_product(name, price, quantity, tags=None):
    ...
    "tags": list(tags) if tags is not None else [],   # fresh list, caller list copied
```
* **Verification:** `test_bug01_products_do_not_share_a_default_tag_list`
  (also asserts a caller-supplied list is copied, not aliased).

---

### BUG-02 — Inventory total silently misses the first product (off-by-one)

* **Observed:** total `4555.0`. **Expected (hand-computed):**
  120×10 + 20×3 + 899×5 = **5755.0**. The difference, 1200, is *exactly* the
  first product's value — the key clue.
* **Hypothesis:** the loop range starts at 1.
* **Inspection (`pdb`, §2.1):** first iteration has `i == 1`, and
  `list(range(1, len(inventory))) == [1, 2]` — index 0 is never visited.

```python
# before
for i in range(1, len(inventory)):
    total = total + inventory[i]["price"] * inventory[i]["quantity"]
```
```python
# after - iterate items, delete the index (and the bug class) entirely
return round(sum(p["price"] * p["quantity"] for p in inventory), 2)
```
* **Verification:** `test_bug02_total_value_includes_every_product`
  (full list, single-item list and empty list).

---

### BUG-03 — `ZeroDivisionError` for an empty inventory

* **Observed:** `average_price([])` crashes. **Expected:** graceful result for
  a legitimate state (a shop with nothing in it yet).
* **Root cause:** `average = total / len(inventory)` with no guard.

```python
# before
average = total / len(inventory)
```
```python
# after
if not inventory:
    return 0.0                      # documented, tested behaviour
return round(sum(p["price"] for p in inventory) / len(inventory), 2)
```
* **Verification:** `test_bug03_average_price_of_empty_inventory_is_zero`.

---

### BUG-04 — Discount returns the amount saved, not the price to pay

* **Observed:** `apply_discount(100, 10) == 10.0`; demo prints a Rs. 899
  backpack “after discount” as **89.9**. **Expected:** 90.0 and 809.1.
* **Root cause:** `price * discount_percent / 100` *is* the discount amount.
  No exception, plausible-looking numbers — the most dangerous kind of bug,
  found only because the expected value was computed by hand first.

```python
# before
discounted = price * discount_percent / 100
return discounted
```
```python
# after
return round(price * (1 - discount_percent / 100), 2)
```
* **Verification:** `test_bug04_discount_returns_the_final_price`
  (10%, 0% and 100% boundaries), plus bounds checking for −5%/101%.

---

### BUG-05 — Loading any real CSV file crashes (header + types + unclosed file)

* **Observed:** `ValueError: could not convert string to float: 'price'`.
* **Traceback reading:** the value `'price'` can only come from the header
  row — so every line, header included, is being treated as data. Reading
  further exposed two latent defects behind the crash: `quantity` was stored
  as a string (would explode later inside arithmetic, far from the cause),
  and the file object was never closed.

```python
# before
handle = open(path)
lines = handle.readlines()
for line in lines:
    parts = line.strip().split(",")
    product = {"name": parts[0], "price": float(parts[1]), "quantity": parts[2], ...}
```
```python
# after - let the csv module do CSV; convert types; close the file
with csv_path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)               # header consumed properly
    for line_number, row in enumerate(reader, start=2):
        inventory.append(create_product(row["name"], float(row["price"]),
                                        int(row["quantity"])))   # int, not str
```
* **Verification:** `test_bug05_load_inventory_parses_header_and_types`
  (5 rows, real types, total = 9398.0) and
  `test_bug05_load_inventory_reports_the_bad_line` (error cites “line 2”).

---

### BUG-06 — Overselling drives stock negative (missing conditional)

* **Observed:** selling 50 pens from a stock of 3 “succeeds”, quantity −47.
* **Root cause:** the only guard is `if quantity < 0` — it validates the
  *request in isolation* and never compares it with stock on hand. The
  conditional exists; it checks the wrong thing.

```python
# before
if quantity < 0:
    print("Invalid quantity"); return False
product["quantity"] = product["quantity"] - quantity
```
```python
# after - validate everything first, mutate last
_validate_quantity(quantity)
product = _require_product(inventory, name)
if quantity > product["quantity"]:
    raise ValueError(f"Cannot sell {quantity} x {name!r}: only {product['quantity']} in stock.")
product["quantity"] -= quantity
```
* **Verification:** `test_bug06_cannot_sell_more_than_is_in_stock` asserts the
  rejected sale leaves stock untouched; a second test covers 0, negative,
  non-integer quantities and unknown products (previously a silent `False`).

---

### BUG-07 — “Most expensive” returns the cheapest products

* **Observed:** `most_expensive(inv, 2) == ['Notebook', 'Pen']`.
  **Expected:** `['Backpack', 'Water Bottle']`.
* **Inspection (REPL):** `str` sorting is lexicographic — `"120.0" < "20.0" <
  "249.5" < "899.0"` because `'1' < '2' < '8'` — and the ascending order then
  takes the *first* n. Two errors compounding in one line.

```python
# before
ordered = sorted(inventory, key=lambda p: str(p["price"]))
return ordered[:n]
```
```python
# after
return sorted(inventory, key=lambda p: p["price"], reverse=True)[:n]
```
* **Verification:** `test_bug07_most_expensive_is_numeric_and_descending`.

---

### BUG-08 — The “backup” is the live data wearing a different name

* **Observed:** `backup[0]["price"] = 1.0` also changes the original.
* **Hypothesis/inspection:** `inventory[:]` copies the outer list only;
  REPL check `backup[0] is inventory[0]` → `True`. The dicts are shared.

```python
# before
backup = inventory[:]
```
```python
# after
return copy.deepcopy(list(inventory))   # dicts AND their tag lists duplicated
```
* **Verification:** `test_bug08_backup_is_a_deep_independent_copy` mutates a
  price, a nested tag list and the list length in the copy, then asserts the
  original is pristine.

---

### BUG-09 — Restock report hangs forever

* **Observed:** `collect_restock_names(inv, 3)` never returns when the first
  product (quantity 10) is above the threshold; confirmed with a daemon
  thread still alive after `join(timeout=1.0)`, and with `timeout 10`.
* **Root cause:** in the `while` loop the above-threshold branch executes
  `continue` *before* `i = i + 1`, so `i` is frozen and the same product is
  examined forever. A textbook non-termination bug: the loop variant does
  not decrease on every path.

```python
# before
while i < len(inventory):
    if inventory[i]["quantity"] > threshold:
        continue                  # <-- i never advances on this path
    names.append(inventory[i]["name"])
    i = i + 1
```
```python
# after - a comprehension has no counter to forget; terminates by construction
return [p["name"] for p in inventory if p["quantity"] <= threshold]
```
* **Verification:** `test_bug09_collect_restock_names_terminates` uses the
  exact input that hung the original.

---

### BUG-10 — `KeyError: 'qty'` kills the summary (and the whole program)

* **Observed:** `main()` crashes after printing three lines.
* **Inspection (post-mortem `pdb`, §2.1):** at the crash frame,
  `list(product.keys()) == ['name', 'price', 'quantity', 'tags']` — the data
  is fine; this one function alone spells the key `qty`.

```python
# before
total_items = total_items + product["qty"]
```
```python
# after
"total_items": sum(p["quantity"] for p in inventory),
```
* **Verification:** `test_bug10_inventory_summary_uses_the_quantity_key`
  (count 3, items 18, value 5755.0). *Prevention note:* a single canonical
  field name — ideally a dataclass/TypedDict — makes this class of typo a
  type-checker error instead of a runtime crash.

---

### BUG-11 — `UnboundLocalError` in the sales counter

* **Observed:** `record_sale(120.0)` →
  `UnboundLocalError: cannot access local variable 'SALES_COUNT'...`.
* **Root cause:** assignment inside a function makes the name local for the
  whole function body; without `global`, the right-hand side reads that
  not-yet-created local. The error message names the mechanism precisely.

```python
# before
def record_sale(amount):
    SALES_COUNT = SALES_COUNT + 1
    return SALES_COUNT
```
```python
# after
def record_sale(amount):
    global SALES_COUNT, SALES_TOTAL
    ...
    SALES_COUNT += 1
    return SALES_COUNT
```
* **Verification:** `test_bug11_record_sale_updates_the_global_counter`.
  (Refactoring judgement: an object would be cleaner than globals, but the
  minimal correct fix preserves the module's existing API; recorded as a
  future improvement in §7 rather than smuggled in as a “fix”.)

---

### BUG-12 — Every save duplicates the entire file

* **Observed:** after save #1 the CSV has 4 lines; after save #2, 8 lines,
  with the header twice. Saving the same data should be idempotent.
* **Root cause:** `open(path, "a")` — append mode — plus a handle that is
  never closed, so correctness depended on interpreter clean-up timing.

```python
# before
handle = open(path, "a")
handle.write("name,price,quantity\n")
...
```
```python
# after
with csv_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
    writer.writeheader()
    ...
```
* **Verification:** `test_bug12_saving_twice_produces_the_same_file`
  compares bytes after one vs. two saves; `test_csv_round_trip` proves
  save → load preserves the data.

---

## 6. What the crashes were hiding

Fixing only what tracebacks point at would have repaired 4 of the 12 defects.
BUG-05 is the clearest example: the `ValueError` on the header row masked the
string-typed `quantity`, which would only have exploded later — inside a
*calculation*, in a different function, with a misleading traceback.
Likewise, BUG-10 crashing `main()` prevented `record_sale` (BUG-11) from ever
being reached in the demo. **A crash found is not the same as the defects
found** — hence the function-by-function reproduction pass instead of
“run it, fix what breaks, repeat”.

## 7. Refactoring and optimisation (after the fixes, tests green)

Behaviour-preserving improvements, each protected by the regression suite:

| Change | Before | After | Benefit |
|---|---|---|---|
| Single lookup helper | The same name-search loop copy-pasted in `sell_product`, `restock_product`, `search_product` | `_find_product` / `_require_product` | One place to fix, one error style; unknown products now fail loudly instead of silently |
| Index loops → iteration | `for i in range(1, ...)` / manual `while` counters | Generator expressions and comprehensions | Removes off-by-one and non-termination as *categories*; no intermediate lists in sums (O(n) time, O(1) extra memory) |
| Hand-rolled CSV → `csv` module | `split(",")`, string concatenation, `"a"` mode | `DictReader`/`DictWriter`, `newline=""`, UTF-8, `with` blocks | Correct quoting, header handling, cross-platform line endings, files always closed |
| Validation up front | Print-and-return `False`; negative stock possible | `_validate_quantity`, range checks, validate-then-mutate | Callers get real exceptions with the offending values; state is never half-updated |
| Money handling | Unrounded floats (`346.3333333333333`) | `round(..., 2)` on prices, totals, discounts | Stable, displayable, comparable amounts |
| Documentation & types | No docstrings or hints; field-name typo invisible | Docstring per function citing its bug ID, type hints, `Product` alias | The code now explains *why*; type checkers/IDEs can catch BUG-10-style slips |
| Demo entry point | Crashed halfway, no arguments | `argparse` with optional CSV path, prints the full correct report | Same demo, now usable as a smoke test and in the manual guide |

**Deliberately not changed:** function names/signatures, the product-dict
format and the CSV schema. The brief requires improved quality *without
altering intended functionality*, and a stable API is what lets the
reproduction harness and the tests express “before vs. after” precisely.
Converting products to a `@dataclass` and the sales counter to a class are
recorded as future work (natural candidates for Week 3's testing/design
follow-up).

## 8. Final verification

```
$ python inventory_manager.py
Products:
  - Notebook: price=120.00 quantity=10
  - Pen: price=20.00 quantity=3
  - Backpack: price=899.00 quantity=5
Total inventory value: 5755.0
Average price: 346.33
Most expensive: Backpack (899.00)
Backpack after 10% discount: 809.1
Summary: {'product_count': 3, 'total_items': 18, 'total_value': 5755.0}
Restock (<=3): ['Pen']
Sales so far: 1

$ python inventory_manager.py data/sample_inventory.csv
Total inventory value: 9398.0
Average price: 367.5
Summary: {'product_count': 5, 'total_items': 29, 'total_value': 9398.0}
Restock (<=3): ['Pen', 'Desk Lamp']

$ python -m pytest -q
22 passed

$ python -m unittest discover -s tests
Ran 22 tests
OK

$ python reproduction/reproduce_bugs.py   # baseline must still be buggy
12/12 bugs reproduced against the original script.
```

Every output above was also checked by hand (e.g. 120×10 + 20×3 + 899×5 =
5755; sample CSV total 1200 + 60 + 4495 + 249.5×8 + 549×3 = 9398).

## 9. Lessons and prevention checklist

1. **Reproduce first, fix second.** A bug you cannot trigger on demand is a
   bug you cannot prove fixed.
2. **Compute the expected answer independently.** Six of twelve defects
   raised nothing; only hand-checked expected values exposed them.
3. **Read the last traceback line first, then walk up** — and use post-mortem
   `pdb` to inspect the exact state that failed instead of guessing.
4. **Beware Python's famous foot-guns:** mutable defaults, shallow copies,
   string sorting of numbers, missing `global`, `bool` being an `int`.
5. **Prefer constructs that cannot express the bug** — iterate items instead
   of indices, comprehensions instead of manual counters, `csv` instead of
   `split(",")`, `with` instead of remembered `close()` calls.
6. **Validate at the boundary, mutate last.** Rejected operations must leave
   state untouched (BUG-06).
7. **One canonical name per concept** — `quantity`, never also `qty`
   (BUG-10). Types/dataclasses turn this into a machine-checkable rule.
8. **Every fix gets a regression test named after the bug.** Future
   maintainers inherit the *reasons*, not just the code.
9. **Separate fixing from refactoring.** Small, reviewable diffs; clean-ups
   afterwards, behind green tests.
10. **Silent failure is the worst failure.** `return False`/bare excepts
    convert diagnosable errors into corrupted data discovered weeks later.
