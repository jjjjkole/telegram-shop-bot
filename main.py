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
        
        # Проверяем и добавляем колонку description, если ее нет
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Сначала создаем таблицу с базовой структурой, если ее нет
        cursor.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price INTEGER NOT NULL, category_id INTEGER NOT NULL, FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE)")
        
        # Теперь, когда таблица точно существует, добавляем колонку, если нужно
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
    get_name = State()
    get_product_data = State()
    get_product_description = State()

# --- CallbackData ---
class Nav(CallbackData, prefix="nav"):
    action: str; level: str; item_id: int | None = None
    city_id: int | None = None; category_id: int | None = None

class ClientNav(CallbackData, prefix="client"):
    level: str; item_id: int | None = None; city_id: int | None = None

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

@dp.callback_query(Nav.filter())
async def handle_admin_nav(callback: CallbackQuery, state: FSMContext, callback_data: Nav):
    action, level, item_id = callback_data.action, callback_data.level, callback_data.item_id
    city_id, category_id = callback_data.city_id, callback_data.category_id
    
    await state.update_data(action=action, level=level, item_id_to_change=item_id, city_id=city_id, category_id=category_id)
    
    # ... (код для удаления и редактирования)

    # --- Обработчики FSM ---
    @dp.message(AdminFSM.get_product_data)
    async def fsm_get_product_data(message: Message, state: FSMContext):
        try:
            name, price_str = message.text.split(' - ')
            price = int(price_str)
        except (ValueError, TypeError):
            return await message.answer("❌ Неверный формат. Попробуйте снова (например, Netflix - 200).")
        
        await state.update_data(name=name, price=price)
        await state.set_state(AdminFSM.get_product_description)
        await message.answer("📝 Введите описание для товара. Если описание не нужно, отправьте прочерк '-'.")

    @dp.message(AdminFSM.get_product_description)
    async def fsm_get_product_description(message: Message, state: FSMContext):
        user_data = await state.get_data()
        action, name, price = user_data['action'], user_data['name'], user_data['price']
        
        description = None if message.text.strip() == '-' else message.text
        
        if action == 'add':
            parent_id = user_data['parent_id']
            db_query("INSERT INTO products (name, price, category_id, description) VALUES (?,?,?,?)", (name, price, parent_id, description))
        elif action == 'edit':
            item_id_to_change = user_data['item_id_to_change']
            db_query("UPDATE products SET name=?, price=?, description=? WHERE id=?", (name, price, description, item_id_to_change))
        
        await message.answer(f"✅ Продукт '{name}' сохранен.", reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="Ок", callback_data="admin_home")).as_markup())
        await state.clear()


# --- Клиентская часть ---
@dp.callback_query(ClientNav.filter())
async def client_nav(callback: CallbackQuery, callback_data: ClientNav):
    level, item_id = callback_data.level, callback_data.item_id
    # ...
    elif level == 'product':
        product_info = db_query("SELECT name, price, description FROM products WHERE id=?", (item_id,), fetchone=True)
        if not product_info: return await callback.answer("Товар не найден!", show_alert=True)
        
        product_name, price, description = product_info
        
        text = f"*{product_name}*\n\n"
        if description:
            text += f"{description}\n\n"
        text += f"Цена: *{price}₽*"

        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Перейти к оплате", url=PAYMENT_LINK)
        builder.button(text="✅ Я оплатил", callback_data="paid_final")
        
        # Удаляем старое сообщение, чтобы не было нагромождения
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode='Markdown')
            
    await callback.answer()
# ... (остальной код)
