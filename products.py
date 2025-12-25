import json
import os

DB_FILE = "products.json"

def load_products():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        # JSON keys are strings, but our logic often uses ints for IDs.
        # We'll load them as strings, but convert to int when needed.
        data = json.load(f)
        # Convert keys to int for the bot logic compatibility
        return {int(k): v for k, v in data.items()}

def save_product(product_id, data):
    products = load_products()
    products[product_id] = data
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=4, ensure_ascii=False)

def get_next_id():
    products = load_products()
    if not products:
        return 1
    return max(products.keys()) + 1

def delete_product(product_id):
    products = load_products()
    if product_id in products:
        del products[product_id]
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, indent=4, ensure_ascii=False)
        return True
    return False
