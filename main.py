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
PAYMENT_LINK = "https://visionary-hamster-5a495f.netlify.app/"

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
    # Добавление
    add_city = State()
    add_category_city = State()
    add_category_name = State()
    add_product_city = State()
    add_product_category = State()
    add_product_data = State()
    # Удаление
    delete_city = State()
    delete_category_city = State()
    delete_category_name = State()
    delete_product_city = State()
    delete_product_category = State()
    delete_product_name = State()


# --- CallbackData ---
class AdminCallback(CallbackData, prefix="admin"):
    action: str

# --- Клавиатуры ---
def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data=AdminCallback(action="add_menu").pack())
    builder.button(text="➖ Удалить", callback_data=AdminCallback(action="delete_menu").pack())
    return builder.as_markup()

def get_add_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Город", callback_data=AdminCallback(action="add_city").pack())
    builder.button(text="Категорию", callback_data=AdminCallback(action="add_category").pack())
    builder.button(text="Товар", callback_data=AdminCallback(action="add_product").pack())
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_home"))
    return builder.as_markup()

def get_delete_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Город", callback_data=AdminCallback(action="delete_city").pack())
    builder.button(text="Категорию", callback_data=AdminCallback(action="delete_category").pack())
    builder.button(text="Товар", callback_data=AdminCallback(action="delete_product").pack())
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_home"))
    return builder.as_markup()


def dynamic_keyboard(items: list):
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=str(item), callback_data=str(item))
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

@dp.callback_query(AdminCallback.filter(F.action == "delete_menu"))
async def admin_delete_menu(callback: CallbackQuery):
    await callback.message.edit_text("Что вы хотите удалить?", reply_markup=get_delete_menu())


# --- Логика добавления ---
@dp.callback_query(AdminCallback.filter(F.action.startswith("add_")))
async def handle_add_action(callback: CallbackQuery, state: FSMContext, callback_data: AdminCallback):
    action = callback_data.action
    data = load_data()

    if action == "add_city":
        await state.set_state(AdminFSM.add_city); await callback.message.edit_text("📍 Введите название города:")
    elif action == "add_category":
        if not data: return await callback.answer("Сначала добавьте город!", show_alert=True)
        await state.set_state(AdminFSM.add_category_city); await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(list(data.keys())))
    elif action == "add_product":
        if not data: return await callback.answer("Сначала добавьте город!", show_alert=True)
        await state.set_state(AdminFSM.add_product_city); await callback.message.edit_text("Выберите город:", reply_markup=dynamic_keyboard(list(data.keys())))

@dp.message(AdminFSM.add_city)
async def add_city_finish(message: Message, state: FSMContext):
    data = load_data(); data[message.text] = {}; save_data(data)
    await message.answer(f"✅ Город '{message.text}' добавлен.", reply_markup=get_admin_menu())
    await state.clear()

@dp.callback_query(AdminFSM.add_category_city)
async def add_category_city_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(city=callback.data); await state.set_state(AdminFSM.add_category_name)
    await callback.message.edit_text("📁 Введите название категории:")

@dp.message(AdminFSM.add_category_name)
async def add_category_finish(message: Message, state: FSMContext):
    user_data = await state.get_data(); city = user_data['city']
    data = load_data(); data[city][message.text] = {}; save_data(data)
    await message.answer(f"✅ Категория '{message.text}' добавлена в '{city}'.", reply_markup=get_admin_menu())
    await state.clear()

@dp.callback_query(AdminFSM.add_product_city)
async def add_product_city_selected(callback: CallbackQuery, state: FSMContext):
    city = callback.data; data = load_data()
    if not data[city]: return await callback.message.edit_text("В этом городе нет категорий! Сначала добавьте.", reply_markup=get_admin_menu())
    await state.update_data(city=city); await state.set_state(AdminFSM.add_product_category)
    await callback.message.edit_text("Выберите категорию:", reply_markup=dynamic_keyboard(list(data[city].keys())))

@dp.callback_query(AdminFSM.add_product_category)
async def add_product_category_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category=callback.data); await state.set_state(AdminFSM.add_product_data)
    await callback.message.edit_text("🛒 Введите товар в формате: Название - Цена")

@dp.message(AdminFSM.add_product_data)
async def add_product_finish(message: Message, state: FSMContext):
    try: name, price_str = message.text.split(' - '); price = int(price_str)
    except (ValueError, TypeError): return await message.answer("❌ Неверный формат. Попробуйте снова (например, Netflix - 200).")
    user_data = await state.get_data(); city, category = user_data['city'], user_data['category']
    data = load_data(); data[city][category][name] = price; save_data(data)
    await message.answer(f"✅ Товар '{name}' добавлен.", reply_markup=get_admin_menu())
    await state.clear()

# --- Логика удаления ---
@dp.callback_query(AdminCallback.filter(F.action.startswith("delete_")))
async def handle_delete_action(callback: CallbackQuery, state: FSMContext, callback_data: AdminCallback):
    action = callback_data.action
    data = load_data()
    if not data: return await callback.answer("Нечего удалять!", show_alert=True)
    
    if action == "delete_city":
        await state.set_state(AdminFSM.delete_city); await callback.message.edit_text("🗑️ Выберите город для удаления:", reply_markup=dynamic_keyboard(list(data.keys())))
    elif action == "delete_category":
        await state.set_state(AdminFSM.delete_category_city); await callback.message.edit_text("🗑️ Сначала выберите город:", reply_markup=dynamic_keyboard(list(data.keys())))
    elif action == "delete_product":
        await state.set_state(AdminFSM.delete_product_city); await callback.message.edit_text("🗑️ Сначала выберите город:", reply_markup=dynamic_keyboard(list(data.keys())))

@dp.callback_query(AdminFSM.delete_city)
async def delete_city_finish(callback: CallbackQuery, state: FSMContext):
    city = callback.data; data = load_data(); del data[city]; save_data(data)
    await callback.message.edit_text(f"✅ Город '{city}' удален.", reply_markup=get_admin_menu())
    await state.clear()

@dp.callback_query(AdminFSM.delete_category_city)
async def delete_category_city_selected(callback: CallbackQuery, state: FSMContext):
    city = callback.data; data = load_data()
    if not data[city]: return await callback.message.edit_text("В этом городе нет категорий!", reply_markup=get_admin_menu())
    await state.update_data(city=city); await state.set_state(AdminFSM.delete_category_name)
    await callback.message.edit_text("Выберите категорию для удаления:", reply_markup=dynamic_keyboard(list(data[city].keys())))

@dp.callback_query(AdminFSM.delete_category_name)
async def delete_category_finish(callback: CallbackQuery, state: FSMContext):
    category = callback.data; user_data = await state.get_data(); city = user_data['city']
    data = load_data(); del data[city][category]; save_data(data)
    await callback.message.edit_text(f"✅ Категория '{category}' удалена.", reply_markup=get_admin_menu())
    await state.clear()

@dp.callback_query(AdminFSM.delete_product_city)
async def delete_product_city_selected(callback: CallbackQuery, state: FSMContext):
    city = callback.data; data = load_data()
    if not data[city]: return await callback.message.edit_text("В этом городе нет категорий!", reply_markup=get_admin_menu())
    await state.update_data(city=city); await state.set_state(AdminFSM.delete_product_category)
    await callback.message.edit_text("Выберите категорию:", reply_markup=dynamic_keyboard(list(data[city].keys())))

@dp.callback_query(AdminFSM.delete_product_category)
async def delete_product_category_selected(callback: CallbackQuery, state: FSMContext):
    category = callback.data; user_data = await state.get_data(); city = user_data['city']
    data = load_data()
    if not data[city][category]: return await callback.message.edit_text("В этой категории нет товаров!", reply_markup=get_admin_menu())
    await state.update_data(category=category); await state.set_state(AdminFSM.delete_product_name)
    await callback.message.edit_text("Выберите товар для удаления:", reply_markup=dynamic_keyboard(list(data[city][category].keys())))

@dp.callback_query(AdminFSM.delete_product_name)
async def delete_product_finish(callback: CallbackQuery, state: FSMContext):
    product = callback.data; user_data = await state.get_data(); city, category = user_data['city'], user_data['category']
    data = load_data(); del data[city][category][product]; save_data(data)
    await callback.message.edit_text(f"✅ Товар '{product}' удален.", reply_markup=get_admin_menu())
    await state.clear()


# --- Клиентская часть ---
class ClientCallback(CallbackData, prefix="client"):
    level: str; city: str | None = None; category: str | None = None; product: str | None = None

def client_keyboard(level: str, items_data, context: dict = None):
    builder = InlineKeyboardBuilder(); context = context or {}; items = items_data.keys()
    for item in items:
        display_text = item
        if level == 'product': display_text = f"{item} — {items_data[item]}₽"
        cb_data = context.copy(); cb_data.update({'level': level, 'product' if level == 'product' else level: item})
        builder.button(text=display_text, callback_data=ClientCallback(**cb_data).pack())
    builder.adjust(1)
    if level == 'category': builder.row(InlineKeyboardButton(text="⬅️ К городам", callback_data=ClientCallback(level='root').pack()))
    if level == 'product': builder.row(InlineKeyboardButton(text="⬅️ К категориям", callback_data=ClientCallback(level='city', city=context['city']).pack()))
    return builder.as_markup()

@dp.message(CommandStart())
async def client_start(message: Message):
    data = load_data();
    if not data: return await message.answer("Магазин пока пуст.")
    await message.answer("👋 Добро пожаловать! Выберите город:", reply_markup=client_keyboard('city', data))

@dp.callback_query(ClientCallback.filter())
async def client_nav(callback: CallbackQuery, callback_data: ClientCallback):
    data = load_data()
    level, city, category, product = callback_data.level, callback_data.city, callback_data.category, callback_data.product
    if level == 'root': await callback.message.edit_text("👋 Добро пожаловать! Выберите город:", reply_markup=client_keyboard('city', data))
    elif level == 'city': await callback.message.edit_text(f"📍 Город: {city}\n\nВыберите категорию:", reply_markup=client_keyboard('category', data[city], {'city': city}))
    elif level == 'category': await callback.message.edit_text(f"📂 Категория: {category}\n\nВыберите товар:", reply_markup=client_keyboard('product', data[city][category], {'city': city, 'category': category}))
    elif level == 'product':
        price = data[city][category][product]; builder = InlineKeyboardBuilder()
        builder.button(text="💳 Перейти к оплате", url=PAYMENT_LINK); builder.button(text="✅ Я оплатил", callback_data="paid_final")
        await callback.message.edit_text(f"Вы выбрали: {product} — {price}₽\n\nНажмите на кнопку ниже для оплаты.", reply_markup=builder.as_markup())
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
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Бот запускается (полная версия с удалением)...")
    asyncio.run(main())
