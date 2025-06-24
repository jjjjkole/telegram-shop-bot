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
        
        cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price INTEGER NOT NULL, category_id INTEGER NOT NULL, description TEXT, FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE)")
        
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'description' not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN description TEXT")
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
    add_category_select_city = State(); add_category_name = State()
    add_product_select_city = State(); add_product_select_category = State(); add_product_data = State(); add_product_description = State()
    # Удаление
    delete_select_city = State(); delete_select_category = State(); delete_select_product = State()
    # Редактирование
    edit_select_city = State(); edit_select_category = State(); edit_select_product = State()
    edit_get_new_name = State(); edit_get_new_product_data = State(); edit_get_new_product_description = State()

# --- CallbackData ---
class AdminCallback(CallbackData, prefix="adm"):
    action: str; level: str

class ClientNav(CallbackData, prefix="client"):
    level: str; item_id: int | None = None; city_id: int | None = None

# --- Клавиатуры ---
def get_main_admin_menu():
    return InlineKeyboardBuilder().add(InlineKeyboardButton(text="➕ Добавить", callback_data="add_menu"), InlineKeyboardButton(text="➖ Удалить", callback_data="delete_menu"), InlineKeyboardButton(text="📝 Редактировать", callback_data="edit_menu")).adjust(3).as_markup()

def get_action_menu(action: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="Город", callback_data=AdminCallback(action=action, level='city').pack())
    builder.button(text="Категорию", callback_data=AdminCallback(action=action, level='category').pack())
    builder.button(text="Товар", callback_data=AdminCallback(action=action, level='product').pack())
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_home"))
    return builder.as_markup()

def dynamic_keyboard(items: list, prefix: str):
    builder = InlineKeyboardBuilder()
    for item_id, name in items:
        display_text = name
        if prefix.startswith("prod"):
            price = db_query("SELECT price FROM products WHERE id=?",(item_id,), fetchone=True)[0]
            display_text = f"{name} — {price}₽"
        builder.button(text=display_text, callback_data=f"{prefix}:{item_id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_home"))
    return builder.as_markup()

# --- Админ-панель: Главное меню ---
@dp.message(Command(ADMIN_PASSWORD))
async def admin_entry(message: Message, state: FSMContext):
    await state.clear(); await message.answer("🔑 Админ-панель:", reply_markup=get_main_admin_menu())

@dp.callback_query(F.data == "admin_home")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    await state.clear(); await callback.message.edit_text("🔑 Админ-панель:", reply_markup=get_main_admin_menu())

@dp.callback_query(F.data.in_({'add_menu', 'delete_menu', 'edit_menu'}))
async def admin_action_menu(callback: CallbackQuery):
    action = callback.data.split('_')[0]
    text = {"add": "добавить", "delete": "удалить", "edit": "редактировать"}
    await callback.message.edit_text(f"Что вы хотите {text.get(action)}?", reply_markup=get_action_menu(action))

# --- Логика добавления ---
@dp.callback_query(AdminCallback.filter(F.action == "add"))
async def add_start(callback: CallbackQuery, state: FSMContext, callback_data: AdminCallback):
    level = callback_data.level
    if level == "city": await state.set_state(AdminFSM.add_city_name); await callback.message.edit_text("📍 Введите название города:")
    elif level == "category":
        cities = db_query("SELECT id, name FROM cities", fetchall=True)
        if not cities: return await callback.answer("Сначала добавьте город!", show_alert=True)
        await state.set_state(AdminFSM.add_category_select_city); await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(cities, "add_cat_city"))
    elif level == "product":
        cities = db_query("SELECT id, name FROM cities", fetchall=True)
        if not cities: return await callback.answer("Сначала добавьте город!", show_alert=True)
        await state.set_state(AdminFSM.add_product_select_city); await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(cities, "add_prod_city"))

@dp.message(AdminFSM.add_city_name)
async def add_city_finish(message: Message, state: FSMContext):
    db_query("INSERT INTO cities (name) VALUES (?)", (message.text,)); await message.answer(f"✅ Город '{message.text}' добавлен.", reply_markup=get_main_admin_menu()); await state.clear()

@dp.callback_query(F.data.startswith("add_cat_city:"))
async def add_category_city_selected(callback: CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split(':')[1]); await state.update_data(city_id=city_id); await state.set_state(AdminFSM.add_category_name); await callback.message.edit_text("📁 Введите название категории:")

@dp.message(AdminFSM.add_category_name)
async def add_category_finish(message: Message, state: FSMContext):
    user_data = await state.get_data(); db_query("INSERT INTO categories (name, city_id) VALUES (?,?)", (message.text, user_data['city_id'])); await message.answer(f"✅ Категория '{message.text}' добавлена.", reply_markup=get_main_admin_menu()); await state.clear()

@dp.callback_query(F.data.startswith("add_prod_city:"))
async def add_product_city_selected(callback: CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split(':')[1]); categories = db_query("SELECT id, name FROM categories WHERE city_id=?", (city_id,), fetchall=True)
    if not categories: return await callback.message.edit_text("В этом городе нет категорий!", reply_markup=get_main_admin_menu())
    await state.update_data(city_id=city_id); await state.set_state(AdminFSM.add_product_select_category); await callback.message.edit_text("Выберите категорию:", reply_markup=dynamic_keyboard(categories, "add_prod_cat"))

@dp.callback_query(F.data.startswith("add_prod_cat:"))
async def add_product_category_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(callback.data.split(':')[1])); await state.set_state(AdminFSM.add_product_data); await callback.message.edit_text("🛒 Введите товар в формате: Название - Цена")

@dp.message(AdminFSM.add_product_data)
async def fsm_get_product_data(message: Message, state: FSMContext):
    try: name, price_str = message.text.split(' - '); price = int(price_str)
    except (ValueError, TypeError): return await message.answer("❌ Неверный формат. Попробуйте снова.")
    await state.update_data(name=name, price=price); await state.set_state(AdminFSM.add_product_description)
    await message.answer("📝 Введите описание для товара. Если не нужно, отправьте прочерк '-'.")

@dp.message(AdminFSM.add_product_description)
async def fsm_add_product_description(message: Message, state: FSMContext):
    user_data = await state.get_data(); name, price = user_data['name'], user_data['price']
    description = None if message.text.strip() == '-' else message.text
    db_query("INSERT INTO products (name, price, category_id, description) VALUES (?,?,?,?)", (name, price, user_data['category_id'], description))
    await message.answer(f"✅ Продукт '{name}' сохранен.", reply_markup=get_main_admin_menu()); await state.clear()

# --- (Здесь будут обработчики для удаления и редактирования) ---

# --- Клиентская часть ---
# (Код клиентской части остается без изменений)

async def main():
    init_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Бот запускается (финальная, стабильная версия)..."); asyncio.run(main())
