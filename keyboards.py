from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from products import load_products

# Main Menu
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Kitoblar"), KeyboardButton(text="🔍 Qidirish")],
        [KeyboardButton(text="🛒 Savat"), KeyboardButton(text="✍️ Fikr qoldirish")],
        [KeyboardButton(text="📞 Biz bilan aloqa"), KeyboardButton(text="📢 Bizning Kanal")]
    ],
    resize_keyboard=True
)

# Function to get unique categories
def get_categories_keyboard():
    products = load_products()
    categories = set()
    for p in products.values():
        categories.add(p.get("category", "Boshqa"))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in sorted(categories):
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat_{cat}")])
    return keyboard

# Function to generate product list buttons
def get_products_keyboard(category=None):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    products = load_products()
    for product_id, product in products.items():
        # Filter by category if provided
        if category and product.get("category", "Boshqa") != category:
            continue
            
        button = InlineKeyboardButton(text=f"{product['name']} - {product['price']} so'm", callback_data=f"prod_{product_id}")
        keyboard.inline_keyboard.append([button])
    
    # Add back button if inside a category
    if category:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Kategoriyalarga qaytish", callback_data="back_to_cats")])
        
    return keyboard

def get_shipping_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Uz Pochta - 15 000 so'm (1 kilogram uchun)", callback_data="ship_Uz Pochta_15000")],
        [InlineKeyboardButton(text="BTS - 40 000 so'm (1 kilogram uchun)", callback_data="ship_BTS_40000")],
        [InlineKeyboardButton(text="Fargo - 25 000 so'm (1 kilogram uchun)", callback_data="ship_Fargo_25000")],
        [InlineKeyboardButton(text="EMU - 27 000 so'm (1 kilogram uchun)", callback_data="ship_EMU_27000")],
        [InlineKeyboardButton(text="Uchar - 15 000 so'm (1 kilogram uchun)", callback_data="ship_Uchar_15000")]
    ])
    return keyboard

# Back button
back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
])

# Buy button for a specific product
def get_buy_keyboard(product_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_cart_{product_id}"),
         InlineKeyboardButton(text="🚀 Buyurtma berish", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_list")]
    ])

def get_cart_keyboard(cart_items_count):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if cart_items_count > 0:
        kb.inline_keyboard.append([InlineKeyboardButton(text="💸 Buyurtma berish", callback_data="checkout")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="🗑 Savatni tozalash", callback_data="clear_cart")])
    return kb
