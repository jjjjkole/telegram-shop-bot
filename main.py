import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

# --- Конфигурация ---
TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_PASSWORD = "admin25"
DB_FILE = "shop.db"
PRODUCT_FILE = "101.txt"
PAYMENT_LINK = "https://visionary-hamster-5a495f.netlify.app/"

# --- Настройка ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # <--- ВОТ ЭТА СТРОКА, КОТОРУЮ Я ВЕРНУЛ
dp = Dispatcher()

# --- Управление БД ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute("CREATE TABLE IF NOT EXISTS cities (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL, city_id INTEGER NOT NULL, FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE)")
        cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price INTEGER NOT NULL, category_id INTEGER NOT NULL, FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE)")
        conn.commit()

def db_query(query, params=(), fetchone=False, fetchall=False, lastrowid=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute(query, params)
        conn.commit()
        if fetchone: return cursor.fetchone()
        if fetchall: return cursor.fetchall()
        if lastrowid: return cursor.lastrowid

# --- FSM Состояния ---
class AdminFSM(StatesGroup):
    add_name = State(); add_product_data = State()
    edit_name = State(); edit_product_data = State()

# --- CallbackData ---
class Nav(CallbackData, prefix="nav"):
    action: str; level: str; item_id: int | None = None
    city_id: int | None = None; category_id: int | None = None

# --- Клавиатуры ---
def create_admin_keyboard(level: str, items: list, action: str, parent_ctx: dict = None):
    builder = InlineKeyboardBuilder(); parent_ctx = parent_ctx or {}
    for item_id, name in items:
        display_text = name
        if level == "product":
            product_info = db_query("SELECT price FROM products WHERE id=?", (item_id,), fetchone=True)
            if product_info: display_text = f"{name} — {product_info[0]}₽"
        
        cb_data = parent_ctx.copy(); cb_data.update({'action': action, 'level': level, 'item_id': item_id})
        builder.button(text=display_text, callback_data=Nav(**cb_data).pack())
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_home"))
    return builder.as_markup()

# --- Админ-панель ---
@dp.message(Command(ADMIN_PASSWORD))
async def admin_entry(message: Message, state: FSMContext):
    await state.clear(); await message.answer("🔑 Админ-панель:", reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="➕ Добавить", callback_data="add"), InlineKeyboardButton(text="➖ Удалить", callback_data="delete"), InlineKeyboardButton(text="📝 Редактировать", callback_data="edit")).adjust(3).as_markup())

@dp.callback_query(F.data == "admin_home")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    await state.clear(); await callback.message.edit_text("🔑 Админ-панель:", reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="➕ Добавить", callback_data="add"), InlineKeyboardButton(text="➖ Удалить", callback_data="delete"), InlineKeyboardButton(text="📝 Редактировать", callback_data="edit")).adjust(3).as_markup())

@dp.callback_query(F.data.in_({'add', 'delete', 'edit'}))
async def admin_action_menu(callback: CallbackQuery, state: FSMContext):
    action = callback.data
    text = {"add": "добавить", "delete": "удалить", "edit": "редактировать"}
    await state.update_data(action=action)
    await callback.message.edit_text(f"Что вы хотите {text.get(action)}?", reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="Город", callback_data=Nav(action=action, level='city').pack()), InlineKeyboardButton(text="Категорию", callback_data=Nav(action=action, level='category').pack()), InlineKeyboardButton(text="Товар", callback_data=Nav(action=action, level='product').pack())).row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_home")).as_markup())

# --- Общий обработчик навигации админа ---
@dp.callback_query(Nav.filter())
async def handle_admin_nav(callback: CallbackQuery, state: FSMContext, callback_data: Nav):
    action, level, item_id = callback_data.action, callback_data.level, callback_data.item_id
    city_id, category_id = callback_data.city_id, callback_data.category_id
    
    await state.update_data(action=action, level=level, item_id_to_edit=item_id, city_id=city_id, category_id=category_id)

    # --- Удаление ---
    if action == "delete":
        db_query(f"DELETE FROM {level}s WHERE id=?", (item_id,))
        await callback.message.edit_text(f"✅ {level.capitalize()} удален.", reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="Ок", callback_data="admin_home")).as_markup())
        return

    # --- Навигация для выбора ---
    items, text_prompt, parent_context = [], "", {}
    if level == "city": 
        items = db_query("SELECT id, name FROM cities", fetchall=True)
        text_prompt = "Выберите город:"
    elif level == "category": 
        items = db_query("SELECT id, name FROM categories WHERE city_id=?", (item_id,), fetchall=True)
        text_prompt = "Выберите категорию:"
        parent_context = {'city_id': item_id}
    elif level == "product": 
        items = db_query("SELECT id, name FROM products WHERE category_id=?", (item_id,), fetchall=True)
        text_prompt = "Выберите товар:"
        parent_context = {'city_id': city_id, 'category_id': item_id}
    
    # Продолжение навигации для выбора (для delete и edit)
    if action in ["delete", "edit"]:
        if not items: return await callback.answer("Здесь нечего выбирать.", show_alert=True)
        await callback.message.edit_text(text_prompt, reply_markup=create_admin_keyboard(level, items, action, parent_context))
        return
        
    # Продолжение навигации для добавления
    if action == "add":
        if level == 'category': await state.update_data(item_id=item_id) # item_id здесь это city_id
        if level == 'product': await state.update_data(item_id=item_id) # item_id здесь это category_id
        
        if level == 'product':
            await state.set_state(AdminFSM.get_product_data); await callback.message.edit_text("🛒 Введите товар в формате: Название - Цена")
        else:
            await state.set_state(AdminFSM.get_name); await callback.message.edit_text(f"Введите название для '{level}':")

# --- Обработчики состояний FSM ---
@dp.message(AdminFSM.get_name)
async def fsm_get_name(message: Message, state: FSMContext):
    user_data = await state.get_data(); action, level = user_data['action'], user_data['level']
    if action == 'add':
        if level == 'city': db_query("INSERT INTO cities (name) VALUES (?)", (message.text,))
        elif level == 'category': db_query("INSERT INTO categories (name, city_id) VALUES (?,?)", (message.text, user_data['item_id']))
    elif action == 'edit':
        db_query(f"UPDATE {level}s SET name=? WHERE id=?", (message.text, user_data['item_id_to_edit']))
    
    await message.answer(f"✅ {level.capitalize()} сохранен.", reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="Ок", callback_data="admin_home")).as_markup())
    await state.clear()

@dp.message(AdminFSM.get_product_data)
async def fsm_get_product(message: Message, state: FSMContext):
    user_data = await state.get_data(); action = user_data['action']
    try: name, price_str = message.text.split(' - '); price = int(price_str)
    except (ValueError, TypeError): return await message.answer("❌ Неверный формат. Попробуйте снова (например, Netflix - 200).")

    if action == 'add': db_query("INSERT INTO products (name, price, category_id) VALUES (?,?,?)", (name, price, user_data['item_id']))
    elif action == 'edit': db_query("UPDATE products SET name=?, price=? WHERE id=?", (name, price, user_data['item_id_to_edit']))
    
    await message.answer(f"✅ Продукт сохранен.", reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="Ок", callback_data="admin_home")).as_markup())
    await state.clear()

# --- Клиентская часть ---
def create_client_keyboard(level: str, items: list, parent_ctx: dict = None):
    builder = InlineKeyboardBuilder(); parent_ctx = parent_ctx or {}
    for item_id, name in items:
        display_text = name
        if level == "product":
            product_info = db_query("SELECT price FROM products WHERE id=?", (item_id,), fetchone=True)
            if product_info: display_text = f"{name} — {product_info[0]}₽"
        
        cb_data = parent_ctx.copy(); cb_data.update({'level': level, 'item_id': item_id})
        builder.button(text=display_text, callback_data=ClientNav(**cb_data).pack())
    builder.adjust(1)
    if level == 'category': builder.row(InlineKeyboardButton(text="⬅️ К городам", callback_data=ClientNav(level='root').pack()))
    if level == 'product': builder.row(InlineKeyboardButton(text="⬅️ К категориям", callback_data=ClientNav(level='city', item_id=parent_ctx['city_id']).pack()))
    return builder.as_markup()

@dp.message(CommandStart())
async def client_start(message: Message):
    cities = db_query("SELECT id, name FROM cities", fetchall=True)
    if not cities: return await message.answer("Магазин пока пуст.")
    await message.answer("👋 Добро пожаловать! Выберите город:", reply_markup=create_client_keyboard('city', cities))

@dp.callback_query(ClientNav.filter())
async def client_nav(callback: CallbackQuery, callback_data: ClientNav):
    level, item_id = callback_data.level, callback_data.item_id
    city_id, category_id = callback_data.city_id, callback_data.category_id

    if level == 'root':
        await callback.message.edit_text("👋 Добро пожаловать! Выберите город:", reply_markup=create_client_keyboard('city', db_query("SELECT id, name FROM cities", fetchall=True)))
    elif level == 'city':
        city_name = db_query("SELECT name FROM cities WHERE id=?", (item_id,), fetchone=True)[0]
        await callback.message.edit_text(f"📍 Город: {city_name}\n\nВыберите категорию:", reply_markup=create_client_keyboard('category', db_query("SELECT id, name FROM categories WHERE city_id=?", (item_id,), fetchall=True), {'city_id': item_id}))
    elif level == 'category':
        category_name = db_query("SELECT name FROM categories WHERE id=?", (item_id,), fetchone=True)[0]
        await callback.message.edit_text(f"📂 Категория: {category_name}\n\nВыберите товар:", reply_markup=create_client_keyboard('product', db_query("SELECT id, name FROM products WHERE category_id=?", (item_id,), fetchall=True), {'city_id': city_id, 'category_id': item_id}))
    elif level == 'product':
        product_name, price = db_query("SELECT name, price FROM products WHERE id=?", (item_id,), fetchone=True)
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Перейти к оплате", url=PAYMENT_LINK); builder.button(text="✅ Я оплатил", callback_data="paid_final")
        await callback.message.edit_text(f"Вы выбрали: {product_name} — {price}₽\n\nНажмите на кнопку ниже для оплаты.", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "paid_final")
async def client_paid(callback: CallbackQuery):
    try:
        with open(PRODUCT_FILE, 'r', encoding='utf-8') as f: product_data = f.read()
        await callback.message.edit_text("✅ Оплата прошла успешно! Ваш товар:"); await callback.message.answer(product_data)
    except FileNotFoundError: await callback.message.answer("❌ Ошибка при выдаче товара.")
    await callback.answer()

# --- Запуск ---
async def main():
    init_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Бот запускается (v. SQLite)..."); asyncio.run(main())
