from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PhotoSize, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from products import save_product, get_next_id, load_products, delete_product
from users_db import get_all_users
from analytics import export_stats
from aiogram.types import FSInputFile
import config

admin_router = Router()

class ProductState(StatesGroup):
    waiting_for_photo = State()
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_price = State()
    waiting_for_description = State()

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        await message.answer("Siz admin emassiz!")
        return
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Yangi kitob qo'shish")],
        [KeyboardButton(text="✏️ Tahrirlash"), KeyboardButton(text="❌ O'chirish")],
        [KeyboardButton(text="📢 Reklama yuborish"), KeyboardButton(text="📊 Statistika")]
    ], resize_keyboard=True)

    await message.answer(
        "Admin Panelga xush kelibsiz!\n\n"
        "Quyidagi bo'limlardan birini tanlang:\n"
        "➕ <b>Yangi kitob qo'shish</b> - (/add_product)\n"
        "✏️ <b>Tahrirlash</b> - (/edit_product)\n"
        "❌ <b>O'chirish</b> - (/delete_product)\n"
        "📊 <b>Statistika</b> - (/stats)",
        reply_markup=kb
    )

@admin_router.message(F.text == "➕ Yangi kitob qo'shish")
@admin_router.message(Command("add_product"))
async def start_add_product(message: Message, state: FSMContext):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        return
    
    await state.set_state(ProductState.waiting_for_photo)
    await message.answer("Yangi kitob rasmini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[], remove_keyboard=True)) # Clean up keyboard during flow if needed, or keep it. Let's remove it to avoid distraction, or keep main menu? 
    # Actually for admin operations, it's better to remove the admin menu temporarily or just keep it. 
    # Let's remove it to force focus, or user might click it again.
    # Updated: Removing keyboard to prevent accidental clicks.


    if str(message.from_user.id) not in config.ADMIN_IDS:
        return
    
    await state.set_state(ProductState.waiting_for_photo)
    await message.answer("Yangi kitob rasmini yuboring:")

@admin_router.message(ProductState.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    # Get the largest photo
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    
    await state.set_state(ProductState.waiting_for_name)
    await message.answer("Kitob nomini yozing:")

@admin_router.message(ProductState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ProductState.waiting_for_category)
    await message.answer("Kitob kategoriyasini yozing (masalan: 'Psixologiya', 'Diniy', 'Badiiy'):")

@admin_router.message(ProductState.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(ProductState.waiting_for_price)
    await message.answer("Kitob narxini yozing (faqat raqam, masalan: 50000):")

@admin_router.message(ProductState.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    price_text = message.text
    if not price_text.isdigit():
        await message.answer("Iltimos, faqat raqam yozing.")
        return
    
    await state.update_data(price=int(price_text))
    await state.set_state(ProductState.waiting_for_description)
    await message.answer("Kitob haqida ma'lumot (tavsif) yozing:")

@admin_router.message(ProductState.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    description = message.text
    data = await state.get_data()
    
    new_id = get_next_id()
    product_data = {
        "name": data['name'],
        "category": data.get('category', 'Boshqa'),
        "price": data['price'],
        "description": description,
        "image": data['photo'] # Uses Telegram File ID
    }
    
    save_product(new_id, product_data)
    
    await message.answer(f"✅ Kitob qo'shildi!\nNomi: {data['name']}\nNarxi: {data['price']}")
    await state.clear()

# --- DELETE PRODUCT ---
@admin_router.message(F.text == "❌ O'chirish")
@admin_router.message(Command("delete_product"))
async def cmd_delete_product(message: Message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        return
    
    products = load_products()
    if not products:
        await message.answer("O'chirish uchun mahsulot yo'q.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for pid, p in products.items():
        btn = InlineKeyboardButton(text=f"❌ {p['name']}", callback_data=f"del_{pid}")
        keyboard.inline_keyboard.append([btn])
    
    await message.answer("O'chirmoqchi bo'lgan kitobni tanlang:", reply_markup=keyboard)

@admin_router.callback_query(F.data.startswith("del_"))
async def process_delete_product(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])
    if delete_product(pid):
        await callback.message.answer("✅ Mahsulot o'chirildi.")
        await callback.message.delete()
    else:
        await callback.message.answer("⚠️ Mahsulot topilmadi.")
    await callback.answer()

# --- EDIT PRODUCT ---
class EditProductState(StatesGroup):
    waiting_for_new_value = State()

@admin_router.message(F.text == "✏️ Tahrirlash")
@admin_router.message(Command("edit_product"))
async def cmd_edit_product(message: Message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        return
        
    products = load_products()
    if not products:
        await message.answer("O'zgartirish uchun mahsulot yo'q.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for pid, p in products.items():
        btn = InlineKeyboardButton(text=f"✏️ {p['name']}", callback_data=f"edit_{pid}")
        keyboard.inline_keyboard.append([btn])
    
    await message.answer("O'zgartirmoqchi bo'lgan kitobni tanlang:", reply_markup=keyboard)

@admin_router.callback_query(F.data.startswith("edit_"))
# Handle initial edit selection (edit_1) AND field selection (edit_field_1_price)
async def process_edit_selection(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    
    # Case 1: Select Product -> Show Fields
    if len(parts) == 2:
        pid = int(parts[1])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Nomi", callback_data=f"edit_field_{pid}_name")],
            [InlineKeyboardButton(text="Kategoriyasi", callback_data=f"edit_field_{pid}_category")],
            [InlineKeyboardButton(text="Narxi", callback_data=f"edit_field_{pid}_price")],
            [InlineKeyboardButton(text="Tavsifi", callback_data=f"edit_field_{pid}_description")],
            [InlineKeyboardButton(text="Rasmi", callback_data=f"edit_field_{pid}_image")]
        ])
        await callback.message.edit_text("Nimasini o'zgartiramiz?", reply_markup=keyboard)
    
    # Case 2: Select Field -> Ask for Value
    elif len(parts) == 4 and parts[1] == "field":
        pid = int(parts[2])
        field = parts[3]
        
        await state.update_data(edit_pid=pid, edit_field=field)
        await state.set_state(EditProductState.waiting_for_new_value)
        
        msg = f"Yangi {field}ni yozing:"
        if field == "image":
            msg = "Yangi rasmni yuboring:"
        
        await callback.message.answer(msg)
        await callback.answer()

@admin_router.message(EditProductState.waiting_for_new_value)
async def process_new_value(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("edit_pid")
    field = data.get("edit_field")
    
    new_value = None
    if field == "image":
        if message.photo:
             new_value = message.photo[-1].file_id
        else:
             await message.answer("Iltimos, rasm yuboring.")
             return
    elif field == "price":
        if message.text.isdigit():
            new_value = int(message.text)
        else:
            await message.answer("Raqam yozing.")
            return
    else:
        new_value = message.text

    # Update logic
    products = load_products()
    if pid in products:
        products[pid][field] = new_value
        save_product(pid, products[pid])
        await message.answer("✅ O'zgartirildi!")
    else:
        await message.answer("⚠️ Xatolik: Mahsulot topilmadi.")
    
    await state.clear()


# --- BROADCAST (REKLAMA) ---
class BroadcastState(StatesGroup):
    waiting_for_message = State()

@admin_router.message(F.text == "📢 Reklama yuborish")
@admin_router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        return
    
    await state.set_state(BroadcastState.waiting_for_message)
    await message.answer("Reklama matnini (yoki rasm/video) yuboring.\nMen uni barcha foydalanuvchilarga tarqataman.", reply_markup=ReplyKeyboardMarkup(keyboard=[], remove_keyboard=True))

@admin_router.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    users = get_all_users()
    count = 0
    blocked = 0
    
    await message.answer(f"Xabar yuborish boshlandi... ({len(users)} ta foydalanuvchi)")
    
    for user_id in users:
        try:
            # Copy the message to preserve formatting, photos, etc.
            await message.send_copy(chat_id=user_id)
            count += 1
        except Exception:
            blocked += 1
    
    await message.answer(f"✅ Reklama yuborildi!\n\nQabul qildi: {count} ta\nBloklagan/Xato: {blocked} ta")
    await state.clear()
    
    # Show Admin Menu again
    await cmd_admin(message)

# --- STATISTICS ---
@admin_router.message(F.text == "📊 Statistika")
async def cmd_stats(message: Message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        return
        
    await message.answer("Statistika yuklanmoqda... ⏳")
    try:
        file_path = export_stats()
        await message.answer_document(FSInputFile(file_path), caption="📊 Savdo va Qidiruv statistikasi")
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

# --- ORDER STATUS HANDLING ---
@admin_router.callback_query(F.data.startswith("status_"))
async def process_order_status(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    action = parts[1] # accept or reject
    user_id = parts[2]
    order_id = parts[3]
    
    if action == "accept":
        try:
            await bot.send_message(chat_id=user_id, text=f"✅ Sizning #{order_id} raqamli buyurtmangiz tasdiqlandi! Tez orada yetkazib beramiz.")
            await callback.answer("Buyurtma tasdiqlandi")
            await callback.message.edit_text(callback.message.text + "\n\n✅ QABUL QILINDI")
        except Exception as e:
            await callback.answer(f"Xatolik: {e}", show_alert=True)
            
    elif action == "reject":
        try:
            await bot.send_message(chat_id=user_id, text=f"❌ Sizning #{order_id} raqamli buyurtmangiz bekor qilindi. Iltimos, admin bilan bog'laning.")
            await callback.answer("Buyurtma bekor qilindi")
            await callback.message.edit_text(callback.message.text + "\n\n❌ BEKOR QILINDI")
        except Exception as e:
            await callback.answer(f"Xatolik: {e}", show_alert=True)
