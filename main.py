import asyncio
import json
import logging
import os
from contextlib import suppress

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

# --- Конфигурация ---
TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_PASSWORD = "admin25"
DATA_FILE = "data.json"
PRODUCT_FILE = "101.txt"
PAYMENT_LINK = "https://example.com/payment_landing"

# --- Настройка ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
dp = Dispatcher()

# --- Утилиты ---
def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

# --- FSM Состояния ---
class AdminFSM(StatesGroup):
    add_city = State()
    add_category_city = State()
    add_category_name = State()
    add_product_city = State()
    add_product_category = State()
    add_product_data = State()

# --- CallbackData ---
class AdminCallback(CallbackData, prefix="admin"):
    action: str # add_city, add_category, add_product, delete_city, etc.
    city: str | None = None
    category: str | None = None

# --- Клавиатуры ---
def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data=AdminCallback(action="add_menu").pack())
    # builder.button(text="➖ Удалить", callback_data=AdminCallback(action="delete_menu").pack())
    return builder.as_markup()

def get_add_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Город", callback_data=AdminCallback(action="add_city").pack())
    builder.button(text="Категорию", callback_data=AdminCallback(action="add_category").pack())
    builder.button(text="Товар", callback_data=AdminCallback(action="add_product").pack())
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_home"))
    return builder.as_markup()

def dynamic_keyboard(items: list, context: dict = None):
    builder = InlineKeyboardBuilder()
    context = context or {}
    for item in items:
        # Для товаров, которые хранятся как dict, item будет ключом
        display_text = item
        # Добавляем к данным для колбэка текущий элемент
        item_context = context.copy()
        item_context['item'] = item # Общий ключ для выбранного элемента
        builder.button(text=display_text, callback_data=str(item)) # Используем простое имя в колбэке для FSM
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_home"))
    return builder.as_markup()


# --- Админ-панель ---
@dp.message(Command(ADMIN_PASSWORD))
async def admin_entry(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔑 Админ-панель. Что вы хотите сделать?", reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_home")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔑 Админ-панель. Что вы хотите сделать?", reply_markup=get_admin_menu())

@dp.callback_query(AdminCallback.filter(F.action == "add_menu"))
async def admin_add_menu(callback: CallbackQuery):
    await callback.message.edit_text("Что вы хотите добавить?", reply_markup=get_add_menu())

# --- Логика добавления ---

# Город
@dp.callback_query(AdminCallback.filter(F.action == "add_city"))
async def add_city_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.add_city)
    await callback.message.edit_text("📍 Введите название города:")

@dp.message(AdminFSM.add_city)
async def add_city_finish(message: Message, state: FSMContext):
    data = load_data()
    data[message.text] = {}
    save_data(data)
    await message.answer(f"✅ Город '{message.text}' добавлен.")
    await state.clear()
    await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu())

# Категория
@dp.callback_query(AdminCallback.filter(F.action == "add_category"))
async def add_category_start(callback: CallbackQuery, state: FSMContext):
    data = load_data()
    if not data: return await callback.answer("Сначала добавьте хотя бы один город!", show_alert=True)
    await state.set_state(AdminFSM.add_category_city)
    await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(list(data.keys())))

@dp.callback_query(AdminFSM.add_category_city)
async def add_category_city_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(city=callback.data)
    await state.set_state(AdminFSM.add_category_name)
    await callback.message.edit_text("📁 Введите название категории:")

@dp.message(AdminFSM.add_category_name)
async def add_category_finish(message: Message, state: FSMContext):
    user_data = await state.get_data()
    city = user_data['city']
    data = load_data()
    data[city][message.text] = {}
    save_data(data)
    await message.answer(f"✅ Категория '{message.text}' добавлена в '{city}'.")
    await state.clear()
    await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu())
    
# Товар
@dp.callback_query(AdminCallback.filter(F.action == "add_product"))
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    data = load_data()
    if not data: return await callback.answer("Сначала добавьте город!", show_alert=True)
    await state.set_state(AdminFSM.add_product_city)
    await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(list(data.keys())))

@dp.callback_query(AdminFSM.add_product_city)
async def add_product_city_selected(callback: CallbackQuery, state: FSMContext):
    city = callback.data
    data = load_data()
    if not data[city]: return await callback.message.edit_text("В этом городе нет категорий! Сначала добавьте.", reply_markup=get_admin_menu())
    await state.update_data(city=city)
    await state.set_state(AdminFSM.add_product_category)
    await callback.message.edit_text("Выберите категорию:", reply_markup=dynamic_keyboard(list(data[city].keys())))

@dp.callback_query(AdminFSM.add_product_category)
async def add_product_category_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category=callback.data)
    await state.set_state(AdminFSM.add_product_data)
    await callback.message.edit_text("🛒 Введите товар в формате: Название - Цена")

@dp.message(AdminFSM.add_product_data)
async def add_product_finish(message: Message, state: FSMContext):
    try:
        name, price_str = message.text.split(' - ')
        price = int(price_str)
    except (ValueError, TypeError):
        return await message.answer("❌ Неверный формат. Попробуйте снова (например, Netflix - 200).")
    
    user_data = await state.get_data()
    city, category = user_data['city'], user_data['category']
    data = load_data()
    data[city][category][name] = price
    save_data(data)
    
    await message.answer(f"✅ Товар '{name}' добавлен.")
    await state.clear()
    await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu())


# --- Клиентская часть ---
class ClientCallback(CallbackData, prefix="client"):
    level: str
    city: str | None = None
    category: str | None = None
    product: str | None = None

def client_keyboard(level: str, items_data, context: dict = None):
    builder = InlineKeyboardBuilder()
    context = context or {}
    items = items_data.keys()
    
    for item in items:
        display_text = item
        if level == 'product': display_text = f"{item} — {items_data[item]}₽"
        
        cb_data = context.copy()
        cb_data.update({'level': level, level: item})
        builder.button(text=display_text, callback_data=ClientCallback(**cb_data).pack())
    
    builder.adjust(1)
    if level == 'category': builder.row(InlineKeyboardButton(text="⬅️ К городам", callback_data=ClientCallback(level='root').pack()))
    if level == 'product': builder.row(InlineKeyboardButton(text="⬅️ К категориям", callback_data=ClientCallback(level='city', city=context['city']).pack()))

    return builder.as_markup()

@dp.message(CommandStart())
async def client_start(message: Message):
    data = load_data()
    if not data: return await message.answer("Магазин пока пуст.")
    await message.answer("👋 Добро пожаловать! Выберите город:", reply_markup=client_keyboard('city', data))

@dp.callback_query(ClientCallback.filter())
async def client_nav(callback: CallbackQuery, callback_data: ClientCallback):
    data = load_data()
    level, city, category, product = callback_data.level, callback_data.city, callback_data.category, callback_data.product

    if level == 'root':
        await callback.message.edit_text("👋 Добро пожаловать! Выберите город:", reply_markup=client_keyboard('city', data))
    elif level == 'city':
        await callback.message.edit_text(f"📍 Город: {city}\n\nВыберите категорию:", reply_markup=client_keyboard('category', data[city], {'city': city}))
    elif level == 'category':
        await callback.message.edit_text(f"📂 Категория: {category}\n\nВыберите товар:", reply_markup=client_keyboard('product', data[city][category], {'city': city, 'category': category}))
    elif level == 'product':
        price = data[city][category][product]
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Перейти к оплате", url=PAYMENT_LINK)
        builder.button(text="✅ Я оплатил", callback_data="paid_final")
        await callback.message.edit_text(f"Вы выбрали: {product} — {price}₽\n\nНажмите на кнопку ниже для оплаты.", reply_markup=builder.as_markup())
    
    await callback.answer()

@dp.callback_query(F.data == "paid_final")
async def client_paid(callback: CallbackQuery):
    try:
        with open(PRODUCT_FILE, 'r', encoding='utf-8') as f: product_data = f.read()
        await callback.message.edit_text("✅ Оплата прошла успешно! Ваш товар:")
        await callback.message.answer(product_data)
    except FileNotFoundError: await callback.message.answer("❌ Ошибка при выдаче товара.")
    await callback.answer()


# --- Запуск ---
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Бот запускается (полная версия)...")
    asyncio.run(main())
