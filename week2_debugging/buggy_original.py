"""inventory_manager.py - small shop inventory manager (ORIGINAL, AS RECEIVED).

Week 2 baseline: this file is preserved exactly in its buggy state so every
defect can be reproduced on demand (see reproduction/reproduce_bugs.py).
It is NOT the deliverable - the corrected version is ../inventory_manager.py.

Intended behaviour (from the original notes / docstrings):
  * products are dicts: {"name": str, "price": float, "quantity": int,
    "tags": list[str]}
  * calculate_total_value  -> sum of price * quantity over ALL products
  * average_price          -> mean unit price (graceful on an empty list)
  * apply_discount         -> FINAL price after the discount
  * load_inventory         -> parse a CSV file with a name,price,quantity
                              header into typed product dicts
  * save_inventory         -> (over)write the inventory CSV; saving twice
                              must produce the same file as saving once
  * sell_product           -> reduce stock, never below zero
  * most_expensive         -> the n highest-priced products, price descending
  * backup_inventory       -> an independent copy of the inventory
  * collect_restock_names  -> names whose quantity is at/below the reorder
                              threshold
  * inventory_summary      -> counts + total value for a report header
  * record_sale            -> bump a running sales counter
"""

SALES_COUNT = 0


def create_product(name, price, quantity, tags=[]):
    product = {
        "name": name,
        "price": price,
        "quantity": quantity,
        "tags": tags,
    }
    return product


def calculate_total_value(inventory):
    total = 0
    for i in range(1, len(inventory)):
        total = total + inventory[i]["price"] * inventory[i]["quantity"]
    return total


def average_price(inventory):
    total = 0
    for product in inventory:
        total = total + product["price"]
    average = total / len(inventory)
    return average


def apply_discount(price, discount_percent):
    discounted = price * discount_percent / 100
    return discounted


def load_inventory(path):
    inventory = []
    handle = open(path)
    lines = handle.readlines()
    for line in lines:
        parts = line.strip().split(",")
        product = {
            "name": parts[0],
            "price": float(parts[1]),
            "quantity": parts[2],
            "tags": [],
        }
        inventory.append(product)
    return inventory


def save_inventory(inventory, path):
    handle = open(path, "a")
    handle.write("name,price,quantity\n")
    for product in inventory:
        line = product["name"] + "," + str(product["price"]) + "," + str(product["quantity"]) + "\n"
        handle.write(line)


def sell_product(inventory, name, quantity):
    for product in inventory:
        if product["name"] == name:
            if quantity < 0:
                print("Invalid quantity")
                return False
            product["quantity"] = product["quantity"] - quantity
            print("Sold", quantity, "x", name)
            return True
    return False


def restock_product(inventory, name, quantity):
    for product in inventory:
        if product["name"] == name:
            product["quantity"] = product["quantity"] + quantity
            return True
    return False


def most_expensive(inventory, n):
    ordered = sorted(inventory, key=lambda p: str(p["price"]))
    return ordered[:n]


def backup_inventory(inventory):
    backup = inventory[:]
    return backup


def collect_restock_names(inventory, threshold):
    names = []
    i = 0
    while i < len(inventory):
        if inventory[i]["quantity"] > threshold:
            continue
        names.append(inventory[i]["name"])
        i = i + 1
    return names


def inventory_summary(inventory):
    total_items = 0
    for product in inventory:
        total_items = total_items + product["qty"]
    summary = {
        "product_count": len(inventory),
        "total_items": total_items,
        "total_value": calculate_total_value(inventory),
    }
    return summary


def record_sale(amount):
    SALES_COUNT = SALES_COUNT + 1
    return SALES_COUNT


def search_product(inventory, name):
    for product in inventory:
        if product["name"] == name:
            return product
    return None


def main():
    inventory = [
        create_product("Notebook", 120.0, 10),
        create_product("Pen", 20.0, 3),
        create_product("Backpack", 899.0, 5),
    ]

    print("Total inventory value:", calculate_total_value(inventory))
    print("Average price:", average_price(inventory))
    print("Backpack after 10% discount:", apply_discount(899.0, 10))
    print("Summary:", inventory_summary(inventory))
    print("Sales so far:", record_sale(120.0))


if __name__ == "__main__":
    main()
