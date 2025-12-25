import json
import os

CART_FILE = "carts.json"

def load_carts():
    if not os.path.exists(CART_FILE):
        return {}
    try:
        with open(CART_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_carts(carts):
    with open(CART_FILE, "w", encoding="utf-8") as f:
        json.dump(carts, f, indent=4)

def add_to_cart(user_id, product_id):
    carts = load_carts()
    user_id = str(user_id)
    if user_id not in carts:
        carts[user_id] = []
    
    # Check if item exists (optional: increase quantity?)
    # For now, let's treat simply: just append. 
    # Or prevent duplicates? Let's allow duplicates (multiple same books).
    carts[user_id].append(int(product_id))
    save_carts(carts)

def get_cart(user_id):
    carts = load_carts()
    return carts.get(str(user_id), [])

def remove_from_cart(user_id, product_id):
    carts = load_carts()
    user_id = str(user_id)
    if user_id in carts:
        try:
            carts[user_id].remove(int(product_id)) # Removes first occurrence
            save_carts(carts)
            return True
        except ValueError:
            return False
    return False

def clear_cart(user_id):
    carts = load_carts()
    user_id = str(user_id)
    if user_id in carts:
        del carts[user_id]
        save_carts(carts)   
