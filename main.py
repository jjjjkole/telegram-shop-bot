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
# Токен бота
TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
# Пароль для входа в админ-панель
ADMIN_PASSWORD = "admin25"


# Файлы для хранения данных
DATA_FILE = "data.json"
PRODUCT_FILE = "101.txt"

# --- Глобальные переменные и утилиты ---
PAYMENT_LINK = "https://example.com/payment_landing"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Функции для работы с JSON файлом
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump({}, f)
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            return json.loads(content) if content else {}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Ошибка при загрузке data.json: {e}"); return {}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e: logger.error(f"Ошибка при сохранении data.json: {e}")

# --- FSM (Машина состояний) ---
class AdminStates(StatesGroup):
    add_city_name = State()
    add_category_select_city = State()
    add_category_name = State()
    add_product_select_city = State()
    add_product_select_category = State()
    add_product_data = State()
    delete_city_select = State()
    delete_category_select_city = State()
    delete_category_select = State()
    delete_product_select_city = State()
    delete_product_select_category = State()
    delete_product_select = State()

class NavCallback(CallbackData, prefix="nav"):
    action: str; level: str; city: str | None = None; category: str | None = None

dp = Dispatcher()


# --- Клавиатуры ---
def get_admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить город", callback_data=NavCallback(action='add', level='city').pack())
    builder.button(text="➖ Удалить город", callback_data=NavCallback(action='delete', level='city').pack())
    builder.button(text="➕ Добавить категорию", callback_data=NavCallback(action='add', level='category').pack())
    builder.button(text="➖ Удалить категорию", callback_data=NavCallback(action='delete', level='category').pack())
    builder.button(text="➕ Добавить товар", callback_data=NavCallback(action='add', level='product').pack())
    builder.button(text="➖ Удалить товар", callback_data=NavCallback(action='delete', level='product').pack())
    builder.adjust(2)
    return builder.as_markup()

def build_keyboard(level: str, data, parent_info: dict = None):
    builder = InlineKeyboardBuilder()
    action = parent_info.get('action', 'select') if parent_info else 'select'
    
    items = data.keys() if isinstance(data, dict) else []

    for item in items:
        # Для товаров показываем цену
        display_text = item
        if level == 'product':
            display_text = f"{item} — {data[item]}₽"
        
        # Собираем данные для колбэка
        callback_data = parent_info.copy() if parent_info else {}
        callback_data['action'] = action
        callback_data['level'] = level
        callback_data[level] = item
        
        builder.button(text=display_text, callback_data=NavCallback(**callback_data).pack())
    
    builder.adjust(1)
    
    # Кнопка "Назад"
    if level == 'category':
        builder.row(InlineKeyboardButton(text="⬅️ К выбору города", callback_data=NavCallback(action='back', level='to_cities').pack()))
    elif level == 'product':
        back_data = parent_info.copy()
        back_data['action'] = 'select'
        back_data['level'] = 'category'
        builder.row(InlineKeyboardButton(text="⬅️ К выбору категории", callback_data=NavCallback(**back_data).pack()))
    
    return builder.as_markup()

# --- Вспомогательные функции ---
async def edit_or_send_message(target, text: str, markup=None):
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)

# --- Хендлеры для админа ---
@dp.message(Command(ADMIN_PASSWORD))
async def admin_login(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu())

# --- Логика добавления ---
@dp.callback_query(NavCallback.filter(F.action == 'add'))
async def handle_add_action(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    await callback.message.delete()
    level = callback_data.level
    if level == 'city':
        await state.set_state(AdminStates.add_city_name)
        await callback.message.answer("📍 Введите название города:")
    elif level == 'category':
        await state.set_state(AdminStates.add_category_select_city)
        await callback.message.answer("Выберите город, чтобы добавить категорию:", reply_markup=build_keyboard('city', load_data()))
    elif level == 'product':
        await state.set_state(AdminStates.add_product_select_city)
        await callback.message.answer("Выберите город, чтобы добавить товар:", reply_markup=build_keyboard('city', load_data()))

@dp.message(AdminStates.add_city_name)
async def process_add_city(message: Message, state: FSMContext):
    data = load_data()
    data[message.text] = {}
    save_data(data)
    await message.answer(f"✅ Город '{message.text}' добавлен.")
    await state.clear()
    await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu())

@dp.callback_query(NavCallback.filter(F.level == 'city'), AdminStates.add_category_select_city)
async def process_add_category_city(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    await state.update_data(city=callback_data.city)
    await state.set_state(AdminStates.add_category_name)
    await callback.message.edit_text("📁 Введите название категории:")

@dp.message(AdminStates.add_category_name)
async def process_add_category_name(message: Message, state: FSMContext):
    user_data = await state.get_data()
    city = user_data['city']
    data = load_data()
    data[city][message.text] = {}
    save_data(data)
    await message.answer(f"✅ Категория '{message.text}' добавлена в город '{city}'.")
    await state.clear()
    await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu())

# ... (Аналогично для добавления товара)

# --- Хендлеры для клиента ---
@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    data = load_data()
    await message.answer("👋 Добро пожаловать! Выберите город:", reply_markup=build_keyboard('city', data))

@dp.callback_query(NavCallback.filter(F.action == 'select'))
async def navigate(callback: CallbackQuery, callback_data: NavCallback):
    data = load_data()
    level = callback_data.level
    
    if level == 'city':
        city = callback_data.city
        await edit_or_send_message(callback, f"📍 Город: {city}\n\nВыберите категорию:", 
                                   reply_markup=build_keyboard('category', data[city], parent_info={'city': city}))
    
    elif level == 'category':
        city = callback_data.city
        category = callback_data.category
        await edit_or_send_message(callback, f"📂 Категория: {category}\n\nВыберите товар:",
                                   reply_markup=build_keyboard('product', data[city][category], parent_info={'city': city, 'category': category}))
    
    elif level == 'product':
        # Логика оплаты
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Перейти к оплате", url=PAYMENT_LINK)
        builder.button(text="✅ Я оплатил", callback_data="paid")
        await edit_or_send_message(callback, "Нажмите на кнопку ниже для оплаты.", builder.as_markup())

@dp.callback_query(F.data == "paid")
async def handle_paid(callback: CallbackQuery):
    await edit_or_send_message(callback, "✅ Оплата прошла успешно! Ваш товар:")
    try:
        with open(PRODUCT_FILE, 'r', encoding='utf-8') as f:
            product_data = f.read()
        await callback.message.answer(product_data)
    except FileNotFoundError:
        await callback.message.answer("❌ Ошибка при выдаче товара.")

@dp.callback_query(NavCallback.filter(F.action == 'back' and F.level == 'to_cities'))
async def back_to_cities(callback: CallbackQuery):
    await edit_or_send_message(callback, "👋 Добро пожаловать! Выберите город:", 
                               reply_markup=build_keyboard('city', load_data()))

# --- Запуск бота ---
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Бот запускается..."); asyncio.run(main())
