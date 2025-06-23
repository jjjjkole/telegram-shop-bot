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
logger = logging.getLogger(__name__)
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

def db_query(query, params=(), fetchone=False, fetchall=False):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute(query, params)
        conn.commit()
        if fetchone: return cursor.fetchone()
        if fetchall: return cursor.fetchall()

# --- FSM Состояния ---
class AdminFSM(StatesGroup):
    # Добавление
    add_city_name = State()
    add_category_select_city = State()
    add_category_name = State()
    add_product_select_city = State()
    add_product_select_category = State()
    add_product_data = State()
    # (Состояния для удаления и редактирования можно добавить по аналогии)


# --- CallbackData ---
class AdminCallback(CallbackData, prefix="admin"):
    action: str # add_menu, add_city, add_category, add_product

# --- Клавиатуры ---
def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data=AdminCallback(action="add_menu").pack())
    # builder.button(text="➖ Удалить", callback_data=AdminCallback(action="delete_menu").pack())
    # builder.button(text="📝 Редактировать", callback_data=AdminCallback(action="edit_menu").pack())
    return builder.as_markup()

def get_add_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Город", callback_data=AdminCallback(action="add_city").pack())
    builder.button(text="Категорию", callback_data=AdminCallback(action="add_category").pack())
    builder.button(text="Товар", callback_data=AdminCallback(action="add_product").pack())
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_home"))
    return builder.as_markup()

def dynamic_keyboard(items: list): # items это список кортежей (id, name)
    builder = InlineKeyboardBuilder()
    for item_id, name in items:
        builder.button(text=name, callback_data=str(item_id))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_home"))
    return builder.as_markup()

# --- Админ-панель ---
@dp.message(Command(ADMIN_PASSWORD))
async def admin_entry(message: Message, state: FSMContext):
    await state.clear(); await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_home")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    await state.clear(); await callback.message.edit_text("🔑 Админ-панель:", reply_markup=get_admin_menu())

@dp.callback_query(AdminCallback.filter(F.action == "add_menu"))
async def admin_add_menu(callback: CallbackQuery):
    await callback.message.edit_text("Что вы хотите добавить?", reply_markup=get_add_menu())

# --- Логика добавления (ПЕРЕПИСАНА ДЛЯ НАДЕЖНОСТИ) ---

# Добавить Город
@dp.callback_query(AdminCallback.filter(F.action == "add_city"))
async def add_city_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.add_city_name)
    await callback.message.edit_text("📍 Введите название города:")

@dp.message(AdminFSM.add_city_name)
async def add_city_finish(message: Message, state: FSMContext):
    db_query("INSERT INTO cities (name) VALUES (?)", (message.text,))
    await message.answer(f"✅ Город '{message.text}' добавлен.", reply_markup=get_admin_menu())
    await state.clear()

# Добавить Категорию
@dp.callback_query(AdminCallback.filter(F.action == "add_category"))
async def add_category_start(callback: CallbackQuery, state: FSMContext):
    cities = db_query("SELECT id, name FROM cities", fetchall=True)
    if not cities: return await callback.answer("Сначала добавьте город!", show_alert=True)
    await state.set_state(AdminFSM.add_category_select_city)
    await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(cities))

@dp.callback_query(AdminFSM.add_category_select_city)
async def add_category_city_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(city_id=int(callback.data))
    await state.set_state(AdminFSM.add_category_name)
    await callback.message.edit_text("📁 Введите название категории:")

@dp.message(AdminFSM.add_category_name)
async def add_category_finish(message: Message, state: FSMContext):
    user_data = await state.get_data()
    db_query("INSERT INTO categories (name, city_id) VALUES (?,?)", (message.text, user_data['city_id']))
    await message.answer(f"✅ Категория '{message.text}' добавлена.", reply_markup=get_admin_menu())
    await state.clear()
    
# Добавить Товар
@dp.callback_query(AdminCallback.filter(F.action == "add_product"))
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    cities = db_query("SELECT id, name FROM cities", fetchall=True)
    if not cities: return await callback.answer("Сначала добавьте город!", show_alert=True)
    await state.set_state(AdminFSM.add_product_select_city)
    await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(cities))

@dp.callback_query(AdminFSM.add_product_select_city)
async def add_product_city_selected(callback: CallbackQuery, state: FSMContext):
    city_id = int(callback.data)
    categories = db_query("SELECT id, name FROM categories WHERE city_id=?", (city_id,), fetchall=True)
    if not categories: return await callback.message.edit_text("В этом городе нет категорий! Сначала добавьте.", reply_markup=get_admin_menu())
    await state.update_data(city_id=city_id)
    await state.set_state(AdminFSM.add_product_select_category)
    await callback.message.edit_text("Выберите категорию:", reply_markup=dynamic_keyboard(categories))

@dp.callback_query(AdminFSM.add_product_select_category)
async def add_product_category_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(callback.data))
    await state.set_state(AdminFSM.add_product_data)
    await callback.message.edit_text("🛒 Введите товар в формате: Название - Цена")

@dp.message(AdminFSM.add_product_data)
async def add_product_finish(message: Message, state: FSMContext):
    try: name, price_str = message.text.split(' - '); price = int(price_str)
    except (ValueError, TypeError): return await message.answer("❌ Неверный формат. Попробуйте снова (например, Netflix - 200).")
    
    user_data = await state.get_data()
    db_query("INSERT INTO products (name, price, category_id) VALUES (?,?,?)", (name, price, user_data['category_id']))
    await message.answer(f"✅ Товар '{name}' добавлен.", reply_markup=get_admin_menu())
    await state.clear()


# --- Клиентская часть ---
class ClientNav(CallbackData, prefix="client"):
    level: str; item_id: int | None = None; city_id: int | None = None

def create_client_keyboard(level: str, items: list, parent_ctx: dict = None):
    builder = InlineKeyboardBuilder(); parent_ctx = parent_ctx or {}
    for item_id, name in items:
        display_text = name
        if level == "product":
            price = db_query("SELECT price FROM products WHERE id=?", (item_id,), fetchone=True)[0]
            display_text = f"{name} — {price}₽"
        
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
    if level == 'root':
        await callback.message.edit_text("👋 Добро пожаловать! Выберите город:", reply_markup=create_client_keyboard('city', db_query("SELECT id, name FROM cities", fetchall=True)))
    elif level == 'city':
        city_name = db_query("SELECT name FROM cities WHERE id=?", (item_id,), fetchone=True)[0]
        categories = db_query("SELECT id, name FROM categories WHERE city_id=?", (item_id,), fetchall=True)
        await callback.message.edit_text(f"📍 Город: {city_name}\n\nВыберите категорию:", reply_markup=create_client_keyboard('category', categories, {'city_id': item_id}))
    elif level == 'category':
        category_name = db_query("SELECT name FROM categories WHERE id=?", (item_id,), fetchone=True)[0]
        products = db_query("SELECT id, name FROM products WHERE category_id=?", (item_id,), fetchall=True)
        await callback.message.edit_text(f"📂 Категория: {category_name}\n\nВыберите товар:", reply_markup=create_client_keyboard('product', products, {'city_id': callback_data.city_id, 'category_id': item_id}))
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
    logger.info("Бот запускается (v. SQLite, исправленная админка)..."); asyncio.run(main())
