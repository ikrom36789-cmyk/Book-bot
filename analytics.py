import json
import os
import pandas as pd
from datetime import datetime
from products import load_products

ANALYTICS_FILE = "analytics.json"

def load_analytics():
    if not os.path.exists(ANALYTICS_FILE):
        return {"searches": [], "orders": []}
    try:
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure keys exist
            if "searches" not in data: data["searches"] = []
            if "orders" not in data: data["orders"] = []
            return data
    except:
        return {"searches": [], "orders": []}

def save_analytics(data):
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def log_search(query):
    data = load_analytics()
    entry = {
        "query": query,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    data["searches"].append(entry)
    save_analytics(data)

def log_order(product_ids):
    data = load_analytics()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for pid in product_ids:
        entry = {
            "product_id": pid,
            "timestamp": timestamp
        }
        data["orders"].append(entry)
    save_analytics(data)

def export_stats():
    data = load_analytics()
    products = load_products()
    
    # 1. Prepare Searches DataFrame
    if data["searches"]:
        df_searches = pd.DataFrame(data["searches"])
        # Group by query to count popularity
        search_counts = df_searches['query'].value_counts().reset_index()
        search_counts.columns = ['Qidiruv So\'zi', 'Soni']
    else:
        search_counts = pd.DataFrame(columns=['Qidiruv So\'zi', 'Soni'])
        
    # 2. Prepare Orders DataFrame
    if data["orders"]:
        orders_list = []
        for order in data["orders"]:
            pid = str(order["product_id"])
            p_name = products[pid]['name'] if pid in products else f"Unknown ({pid})"
            category = products[pid].get('category', 'Boshqa') if pid in products else "Noma'lum"
            orders_list.append({
                "product_name": p_name,
                "category": category,
                "timestamp": order["timestamp"]
            })
        
        df_orders = pd.DataFrame(orders_list)
        # Group by product to count sales
        sales_counts = df_orders['product_name'].value_counts().reset_index()
        sales_counts.columns = ['Kitob Nomi', 'Sotilgan Soni']
        
        # Group by category
        cat_counts = df_orders['category'].value_counts().reset_index()
        cat_counts.columns = ['Kategoriya', 'Sotilgan Soni']
    else:
        sales_counts = pd.DataFrame(columns=['Kitob Nomi', 'Sotilgan Soni'])
        cat_counts = pd.DataFrame(columns=['Kategoriya', 'Sotilgan Soni'])

    # Write to Excel
    filename = "statistics.xlsx"
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        sales_counts.to_excel(writer, sheet_name="Top Kitoblar", index=False)
        cat_counts.to_excel(writer, sheet_name="Kategoriyalar", index=False)
        search_counts.to_excel(writer, sheet_name="Qidiruvlar", index=False)
        
        # Raw data (optional)
        # if data["searches"]:
        #     df_searches.to_excel(writer, sheet_name="Qidiruv Tarixi", index=False)
        
    return filename
