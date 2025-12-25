from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputFile, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from products import load_products
from users_db import add_user
import keyboards as kb
import config
import os
import uuid
from cart_db import add_to_cart, get_cart, clear_cart, remove_from_cart
from analytics import log_search, log_order

router = Router()

class OrderState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_shipping = State()
    waiting_for_product_id = State()
    waiting_for_receipt = State()

class SearchState(StatesGroup):
    waiting_for_query = State()

class FeedbackState(StatesGroup):
    waiting_for_text = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    add_user(message.from_user.id)
    
    share_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♻️ Do'stlarimga ulashish", switch_inline_query="\nSalom! Men Niholbooks orqali kitob olyapman. Tavsiya qilaman!")]
    ])
    
    if os.path.exists("logo.jpg"):
        await message.answer_photo(
            FSInputFile("logo.jpg"), 
            caption=f"Assalomu alaykum, {message.from_user.full_name}! Niholbooks botiga xush kelibsiz.\nQuyidagi menudan kerakli bo'limni tanlang:",
            reply_markup=kb.main_menu
        )
        # Send separate message for share button if you want it sticky, or attach to photo?
        # Attaching to photo overrides reply_markup main_menu if we are not careful.
        # ReplyKeyboardMarkup sends a separate menu. Inline attaches to message.
        # We can attach Share button to a text message below the photo or just leave it.
        # Better: Send a short text "Bizni do'stlaringizga tavsiya qiling" with the button.
        await message.answer("Bizni do'stlaringizga tavsiya qiling: 👇", reply_markup=share_kb)
    else:
        await message.answer(f"Assalomu alaykum, {message.from_user.full_name}! Xush kelibsiz.", reply_markup=kb.main_menu)
        await message.answer("Bizni do'stlaringizga tavsiya qiling: 👇", reply_markup=share_kb)
    
    # If admin ID is not set, tell the user their ID so they can set it
    if not config.ADMIN_IDS:
        await message.answer(f"⚠️ Admin ID sozlanmagan.\nSizning ID raqamingiz: `{message.from_user.id}`\nBuni .env faylga yozing.")

@router.message(F.text == "📚 Kitoblar")
async def show_categories(message: Message):
    await message.answer("Bo'limni tanlang:", reply_markup=kb.get_categories_keyboard())

@router.callback_query(F.data.startswith("cat_"))
async def show_books_in_category(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    await callback.message.edit_text(f"📂 {category}\nKitobni tanlang:", reply_markup=kb.get_products_keyboard(category=category))
    await callback.answer()

@router.callback_query(F.data == "back_to_cats")
async def back_to_cats(callback: CallbackQuery):
    await callback.message.edit_text("Bo'limni tanlang:", reply_markup=kb.get_categories_keyboard())
    await callback.answer()

@router.message(F.text == "🔍 Qidirish")
async def start_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer("Kitob nomini yozing (masalan: 'Sarmoyachi'):")

@router.message(SearchState.waiting_for_query)
async def process_search(message: Message, state: FSMContext):
    query = message.text.lower()
    log_search(query) # Log analytics
    products = load_products()
    results = {}
    
    for pid, p in products.items():
        if query in p['name'].lower() or query in p.get('description', '').lower():
            results[pid] = p
            
    if not results:
        await message.answer("😔 Hech narsa topilmadi. Boshqa nom bilan izlab ko'ring yoki bo'limlardan qidiring.", reply_markup=kb.main_menu)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for pid, p in results.items():
            button = InlineKeyboardButton(text=f"{p['name']} - {p['price']} so'm", callback_data=f"prod_{pid}")
            keyboard.inline_keyboard.append([button])
        
        await message.answer(f"🔎 Qidiruv natijalari ({len(results)} ta):", reply_markup=keyboard)
    
    await state.clear()

@router.message(F.text == "📞 Biz bilan aloqa")
async def show_contact(message: Message):
    await message.answer("Murojaat uchun: \n@BintuuShavkat\nTel: +998941853575")

@router.message(F.text == "📢 Bizning Kanal")
async def show_channel(message: Message):
    await message.answer("Bizning rasmiy kanalimizga obuna bo'ling:\nhttps://t.me/Niholbooks_online")

@router.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = load_products().get(product_id)
    
    if product:
        # Just text for now, can add photo if valid URL
        text = f"<b>{product['name']}</b>\n\n{product['description']}\n\nNarxi: {product['price']} so'm"
        # Try to send photo, fallback to text if fail
        try:
            image_source = product['image']
            if image_source.startswith("http"):
                # URL - pass as is
                pass
            elif os.path.exists(image_source):
                # Local file
                image_source = FSInputFile(image_source)
            else:
                # Assume Telegram File ID - pass as is
                pass
            
            await callback.message.answer_photo(photo=image_source, caption=text, reply_markup=kb.get_buy_keyboard(product_id))
        except Exception as e:
             # await callback.message.answer(f"Rasm yuborishda xatolik: {e}") # Debug
             await callback.message.answer(text, reply_markup=kb.get_buy_keyboard(product_id))
    
    await callback.answer()

@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Bizning kitoblar:", reply_markup=kb.get_products_keyboard())

# --- CART SYSTEM ---
@router.callback_query(F.data.startswith("add_cart_"))
async def add_item_to_cart(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    add_to_cart(callback.from_user.id, product_id)
    await callback.answer("✅ Savatga qo'shildi!", show_alert=True)

@router.message(F.text == "🛒 Savat")
async def show_cart(message: Message):
    cart_ids = get_cart(message.from_user.id)
    if not cart_ids:
        await message.answer("Savatingiz bo'sh 🗑")
        return

    products = load_products()
    text = "🛒 <b>Sizning savatingiz:</b>\n\n"
    total_price = 0
    
    for pid in cart_ids:
        product = products.get(pid) # Ensure int if key is int, or str if str. JSON keys are str.
        if not product:
            product = products.get(str(pid))
        
        if product:
            text += f"➖ {product['name']} - {product['price']} so'm\n"
            total_price += product['price']
            
    text += f"\n<b>Jami: {total_price} so'm</b>"
    
    await message.answer(text, reply_markup=kb.get_cart_keyboard(len(cart_ids)))

@router.callback_query(F.data == "clear_cart")
async def process_clear_cart(callback: CallbackQuery):
    clear_cart(callback.from_user.id)
    await callback.message.edit_text("Savatingiz tozalandi 🗑")
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def start_buy_process(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    # "Buy Now" means buying ONLY this item. So clear cart and add this.
    clear_cart(callback.from_user.id)
    add_to_cart(callback.from_user.id, product_id)
    
    await state.set_state(OrderState.waiting_for_phone)
    await callback.message.answer("Bog'lanish uchun telefon raqamingizni yozing:\n(Masalan: +998901234567)")
    await callback.answer()

@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.waiting_for_phone)
    await callback.message.answer("Bog'lanish uchun telefon raqamingizni yozing:\n(Masalan: +998901234567)")
    await callback.answer()



@router.message(OrderState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    phone = message.text
    await state.update_data(phone=phone)
    await state.set_state(OrderState.waiting_for_address)
    await message.answer("Yashash manzilingizni kiriting:\n(Viloyat, tuman, ko'cha, uy raqami)")

@router.message(OrderState.waiting_for_address)
async def process_address(message: Message, state: FSMContext, bot: Bot):
    address = message.text
    await state.update_data(address=address)
    await state.set_state(OrderState.waiting_for_shipping)
    await message.answer("Yetkazib berish turini tanlang:", reply_markup=kb.get_shipping_keyboard())

@router.callback_query(OrderState.waiting_for_shipping, F.data.startswith("ship_"))
async def process_shipping(callback: CallbackQuery, state: FSMContext, bot: Bot):
    parts = callback.data.split("_")
    shipping_name = parts[1]
    shipping_price = parts[2]
    
    data = await state.get_data()
    phone = data.get("phone")
    address = data.get("address")
    
    # Calculate Total based on Cart
    cart_ids = get_cart(callback.from_user.id)
    if not cart_ids:
        await callback.message.answer("Xatolik: Savatingiz bo'shab qoldi.")
        await state.clear()
        return

    products_db = load_products() # Renamed to avoid confusion
    order_items_text = ""
    total_price = 0
    
    for pid in cart_ids:
        p = products_db.get(str(pid)) or products_db.get(int(pid))
        if p:
            order_items_text += f"- {p['name']} ({p['price']} so'm)\n"
            total_price += p['price']
            
    # Add shipping
    total_with_shipping = total_price + int(shipping_price)
    
    # Log Order Analytics
    log_order(cart_ids)
    
    # Generate Order ID
    order_id = str(uuid.uuid4())[:8]
    
    # Notify Admin (Personal)
    if config.ADMIN_IDS:
        admin_text = (f"🆕 Yangi buyurtma! (#{order_id})\n\n"
                      f"👤 Xaridor: {callback.from_user.full_name} (@{callback.from_user.username})\n"
                      f"📞 Tel: {phone}\n"
                      f"📍 Manzil: {address}\n"
                      f"🚚 Pochta: {shipping_name} ({shipping_price} so'm)\n\n"
                      f"📚 Kitoblar:\n{order_items_text}\n"
                      f"💰 Jami (pochta bilan): {total_with_shipping} so'm")
        
        # Admin Buttons
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"status_accept_{callback.from_user.id}_{order_id}"),
             InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"status_reject_{callback.from_user.id}_{order_id}")]
        ])
        
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_text, reply_markup=admin_kb)
            except Exception as e:
                pass
    
    # Confirmation and Payment Info
    await callback.message.delete()
    await callback.message.answer(
        f"✅ Buyurtmangiz qabul qilindi!\nID: #{order_id}\n\n"
        f"Pochta: {shipping_name}\n"
        f"Jami to'lov: {total_with_shipping} so'm\n\n"
        f"To'lov uchun karta raqamimiz:\n"
        f"💳 <b>5614 6816 2299 2364</b>\n"
        f"Mamedova Gulmira\n"
        f"❗️ <b>Chekni tashlash majburiy!</b>\n\n"
        f"Tez orada aloqaga chiqamiz."
    )
    # Clear cart after order
    clear_cart(callback.from_user.id)
    
    # Wait for Receipt
    await state.update_data(order_id=order_id)
    await state.set_state(OrderState.waiting_for_receipt)
    await callback.message.answer("📸 Iltimos, to'lov chekini shu yerga yuboring so'ng adminlar tasdiqlashadi.")

@router.message(OrderState.waiting_for_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id", "Unknown")
    
    # Notify Admin
    if config.ADMIN_IDS:
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=f"📥 <b>Chek yuborildi!</b>\nBuyurtma ID: #{order_id}\nXaridor: {message.from_user.full_name}")
                await message.send_copy(chat_id=admin_id)
            except Exception:
                pass
                
    await message.answer("✅ Chek qabul qilindi! Adminlar tez orada tekshirib tasdiqlashadi.")
    await state.clear()

# --- FEEDBACK SYSTEM ---
@router.message(F.text == "✍️ Fikr qoldirish")
async def start_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackState.waiting_for_text)
    await message.answer("Biz haqimizda fikringizni yozib qoldiring (matn yoki audio):")

@router.message(FeedbackState.waiting_for_text)
async def process_feedback(message: Message, state: FSMContext, bot: Bot):
    # Notify all admins
    if config.ADMIN_IDS:
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=f"📩 <b>Yangi Fikr-mulohaza!</b>\n👤 Kimdan: {message.from_user.full_name} (@{message.from_user.username})")
                await message.send_copy(chat_id=admin_id)
            except Exception:
                pass
    
    await message.answer("✅ Fikringiz uchun rahmat! Bu biz uchun muhim.")
    await state.clear()
