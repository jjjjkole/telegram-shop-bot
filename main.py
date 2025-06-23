import asyncio
import json
import logging
import os
from contextlib import suppress

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, BaseFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Конфигурация ---
TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_ID = 5206914915

# Файлы для хранения данных
DATA_FILE = "data.json"
PRODUCT_FILE = "101.txt"

# --- Глобальные переменные и утилиты ---
PAYMENT_LINK = "https://example.com/payment_landing"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Фильтр для проверки, является ли пользователь админом
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message | CallbackQuery) -> bool:
        return message.from_user.id == ADMIN_ID

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
class AdminState(StatesGroup):
    # Состояния для добавления
    add_city_name = State(); add_category_select_city = State(); add_category_name = State()
    add_product_select_city = State(); add_product_select_category = State(); add_product_data = State()
    # НОВЫЕ состояния для пошагового удаления
    delete_city_select = State()
    delete_category_select_city = State()
    delete_category_select = State()
    delete_product_select_city = State()
    delete_product_select_category = State()
    delete_product_select = State()


class NavCallback(CallbackData, prefix="nav"):
    action: str; level: str; city: str | None = None; category: str | None = None; product: str | None = None

dp = Dispatcher()

# ... (клавиатуры и вспомогательные функции остаются без изменений) ...
def get_admin_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить город", callback_data=NavCallback(action='add_start', level='city').pack())
    builder.button(text="➖ Удалить город", callback_data=NavCallback(action='delete_start', level='city').pack())
    builder.button(text="➕ Добавить категорию", callback_data=NavCallback(action='add_start', level='category').pack())
    builder.button(text="➖ Удалить категорию", callback_data=NavCallback(action='delete_start', level='category').pack())
    builder.button(text="➕ Добавить товар", callback_data=NavCallback(action='add_start', level='product').pack())
    builder.button(text="➖ Удалить товар", callback_data=NavCallback(action='delete_start', level='product').pack())
    builder.button(text="⬅️ Выйти", callback_data="exit_admin")
    builder.adjust(2)
    return builder.as_markup()

async def edit_or_send_message(target: Message | CallbackQuery, text: str, markup: InlineKeyboardMarkup = None):
    if isinstance(target, CallbackQuery):
        with suppress(TelegramBadRequest): await target.message.edit_text(text, reply_markup=markup); await target.answer()
    else: await target.answer(text, reply_markup=markup)

def build_dynamic_keyboard(action: str, level: str, data_dict: dict, parent_data: dict = None):
    builder = InlineKeyboardBuilder()
    parent_data = parent_data or {}
    for item_name, item_value in data_dict.items():
        callback_payload = parent_data.copy(); callback_payload['level'] = level; callback_payload['action'] = action
        display_text = item_name
        if level == 'city': callback_payload['city'] = item_name
        elif level == 'category': callback_payload['category'] = item_name
        elif level == 'product': callback_payload['product'] = item_name; display_text = f"{item_name} — {item_value}₽"
        builder.button(text=display_text, callback_data=NavCallback(**callback_payload).pack())
    builder.adjust(1)
    nav_buttons = []
    if level != 'city':
         nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main_menu"))
    if action.startswith(('add', 'delete')):
        if not any(b.text == "🏠 В админ-меню" for b in nav_buttons):
            nav_buttons.append(InlineKeyboardButton(text="🏠 В админ-меню", callback_data="admin_main_menu"))
    if nav_buttons:
        builder.row(*nav_buttons)
    return builder.as_markup()

# --- Админ-хендлеры ---
@dp.message(Command("admin"), IsAdmin())
async def admin_login(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu_keyboard())

@dp.callback_query(F.data.in_(["admin_main_menu", "exit_admin"]), IsAdmin())
async def handle_admin_nav(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "🔑 Админ-панель:" if callback.data == "admin_main_menu" else "Вы вышли из админ-панели. Для входа - /admin."
    markup = get_admin_menu_keyboard() if callback.data == "admin_main_menu" else None
    await edit_or_send_message(callback, text, markup)

# --- Логика добавления (без изменений) ---
@dp.callback_query(NavCallback.filter(F.action == 'add_start'), IsAdmin())
async def start_add_item(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    level, data = callback_data.level, load_data()
    if level == 'city': await state.set_state(AdminState.add_city_name); await edit_or_send_message(callback, "📍 Введите название города:")
    elif level == 'category':
        if not data: return await callback.answer("Сначала добавьте город!", show_alert=True)
        await state.set_state(AdminState.add_category_select_city); await edit_or_send_message(callback, "Выберите город:", build_dynamic_keyboard('select', 'city', data, {'action':'add_start'}))
    elif level == 'product':
        if not any(data.values()): return await callback.answer("Сначала добавьте категорию!", show_alert=True)
        await state.set_state(AdminState.add_product_select_city); await edit_or_send_message(callback, "Выберите город:", build_dynamic_keyboard('select', 'city', data, {'action':'add_start'}))

@dp.message(AdminState.add_city_name, IsAdmin())
async def process_add_city(message: Message, state: FSMContext):
    city_name, data = message.text.strip(), load_data()
    if city_name not in data: data[city_name] = {}; save_data(data); await message.answer(f"✅ Город '{city_name}' добавлен.")
    else: await message.answer(f"⚠️ Город '{city_name}' уже есть.")
    await state.clear(); await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu_keyboard())

@dp.callback_query(AdminState.add_category_select_city, IsAdmin())
async def select_city_for_category(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    await state.update_data(city=callback_data.city); await state.set_state(AdminState.add_category_name); await edit_or_send_message(callback, "📁 Введите название категории:")

@dp.message(AdminState.add_category_name, IsAdmin())
async def process_add_category(message: Message, state: FSMContext):
    category_name, user_data, data = message.text.strip(), await state.get_data(), load_data()
    city = user_data['city']
    if category_name not in data[city]: data[city][category_name] = {}; save_data(data); await message.answer(f"✅ Категория '{category_name}' добавлена.")
    else: await message.answer(f"⚠️ Категория '{category_name}' уже есть.")
    await state.clear(); await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu_keyboard())

@dp.callback_query(AdminState.add_product_select_city, IsAdmin())
async def select_city_for_product(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    city, data = callback_data.city, load_data()
    await state.update_data(city=city); await state.set_state(AdminState.add_product_select_category); await edit_or_send_message(callback, "Выберите категорию:", build_dynamic_keyboard('select', 'category', data[city], {'city': city, 'action':'add_start'}))

@dp.callback_query(AdminState.add_product_select_category, IsAdmin())
async def select_category_for_product(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    await state.update_data(category=callback_data.category); await state.set_state(AdminState.add_product_data); await edit_or_send_message(callback, "🛒 Введите товар в формате: Название - Цена")

@dp.message(AdminState.add_product_data, IsAdmin())
async def process_add_product(message: Message, state: FSMContext):
    try: product_name, price_str = message.text.strip().split(' - '); price = int(price_str)
    except (ValueError, TypeError): return await message.answer("❌ Неверный формат. Попробуйте снова (например, Netflix - 200).")
    user_data = await state.get_data(); city, category = user_data['city'], user_data['category']
    data = load_data(); data[city][category][product_name] = price; save_data(data)
    await message.answer(f"✅ Товар '{product_name}' добавлен.")
    await state.clear(); await message.answer("🔑 Админ-панель:", reply_markup=get_admin_menu_keyboard())

# --- ОБНОВЛЕННАЯ ЛОГИКА УДАЛЕНИЯ ---
@dp.callback_query(NavCallback.filter(F.action == 'delete_start'), IsAdmin())
async def start_delete_item(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    level, data = callback_data.level, load_data()
    if not data: return await callback.answer("Нечего удалять!", show_alert=True)

    if level == 'city':
        await state.set_state(AdminState.delete_city_select)
        await edit_or_send_message(callback, "🗑️ Выберите город для удаления:", build_dynamic_keyboard('delete', 'city', data))
    elif level == 'category':
        await state.set_state(AdminState.delete_category_select_city)
        await edit_or_send_message(callback, "🗑️ Сначала выберите город:", build_dynamic_keyboard('select', 'city', data))
    elif level == 'product':
        await state.set_state(AdminState.delete_product_select_city)
        await edit_or_send_message(callback, "🗑️ Сначала выберите город:", build_dynamic_keyboard('select', 'city', data))

# Удаление города (один шаг)
@dp.callback_query(NavCallback.filter(F.action == 'delete' and F.level == 'city'), IsAdmin(), AdminState.delete_city_select)
async def process_delete_city(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    data = load_data()
    del data[callback_data.city]
    save_data(data)
    await state.clear()
    await edit_or_send_message(callback, f"✅ Город '{callback_data.city}' удален.", get_admin_menu_keyboard())

# Удаление категории (шаг 1: выбор города)
@dp.callback_query(AdminState.delete_category_select_city, IsAdmin())
async def delete_category_city_step(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    city_name = callback_data.city
    data = load_data()
    if not data.get(city_name): return await edit_or_send_message(callback, "В этом городе нет категорий.", get_admin_menu_keyboard())
    await state.update_data(city=city_name)
    await state.set_state(AdminState.delete_category_select)
    await edit_or_send_message(callback, f"🗑️ Теперь выберите категорию для удаления в городе '{city_name}':", build_dynamic_keyboard('delete', 'category', data[city_name], {'city': city_name}))

# Удаление категории (шаг 2: выбор и удаление категории)
@dp.callback_query(AdminState.delete_category_select, IsAdmin())
async def delete_category_finish_step(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    category_name = callback_data.category
    user_data = await state.get_data()
    city_name = user_data['city']
    data = load_data()
    del data[city_name][category_name]
    save_data(data)
    await state.clear()
    await edit_or_send_message(callback, f"✅ Категория '{category_name}' удалена.", get_admin_menu_keyboard())

# Удаление товара (шаг 1: выбор города)
@dp.callback_query(AdminState.delete_product_select_city, IsAdmin())
async def delete_product_city_step(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    city_name = callback_data.city
    data = load_data()
    if not data.get(city_name): return await edit_or_send_message(callback, "В этом городе нет категорий.", get_admin_menu_keyboard())
    await state.update_data(city=city_name)
    await state.set_state(AdminState.delete_product_select_category)
    await edit_or_send_message(callback, f"🗑️ Выберите категорию в городе '{city_name}':", build_dynamic_keyboard('select', 'category', data[city_name], {'city': city_name}))

# Удаление товара (шаг 2: выбор категории)
@dp.callback_query(AdminState.delete_product_select_category, IsAdmin())
async def delete_product_category_step(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    category_name = callback_data.category
    user_data = await state.get_data()
    city_name = user_data['city']
    data = load_data()
    if not data.get(city_name, {}).get(category_name): return await edit_or_send_message(callback, "В этой категории нет товаров.", get_admin_menu_keyboard())
    await state.update_data(category=category_name)
    await state.set_state(AdminState.delete_product_select)
    await edit_or_send_message(callback, f"🗑️ Теперь выберите товар для удаления:", build_dynamic_keyboard('delete', 'product', data[city_name][category_name], {'city': city_name, 'category': category_name}))

# Удаление товара (шаг 3: выбор и удаление товара)
@dp.callback_query(AdminState.delete_product_select, IsAdmin())
async def delete_product_finish_step(callback: CallbackQuery, state: FSMContext, callback_data: NavCallback):
    product_name = callback_data.product
    user_data = await state.get_data()
    city_name, category_name = user_data['city'], user_data['category']
    data = load_data()
    del data[city_name][category_name][product_name]
    save_data(data)
    await state.clear()
    await edit_or_send_message(callback, f"✅ Товар '{product_name}' удален.", get_admin_menu_keyboard())

# --- Клиент-хендлеры (без изменений) ---
@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear(); data = load_data()
    if not data: return await message.answer("😔 Извините, магазин пока пуст.")
    await message.answer("👋 Добро пожаловать! Выберите город:", reply_markup=build_dynamic_keyboard('select', 'city', data))

@dp.callback_query(NavCallback.filter(F.action == 'select'))
async def navigate_client_menu(callback: CallbackQuery, callback_data: NavCallback):
    data = load_data(); city, category = callback_data.city, callback_data.category
    if callback_data.level == 'city': await edit_or_send_message(callback, f"📍 Город: {city}\n\nВыберите категорию:", build_dynamic_keyboard('select', 'category', data[city], {'city': city}))
    elif callback_data.level == 'category': await edit_or_send_message(callback, f"📂 Категория: {category}\n\nВыберите товар:", build_dynamic_keyboard('select', 'product', data[city][category], {'city': city, 'category': category}))
    elif callback_data.level == 'product':
        price = data.get(city, {}).get(category, {}).get(callback_data.product); builder = InlineKeyboardBuilder()
        builder.button(text="💳 Перейти к оплате", url=PAYMENT_LINK); builder.button(text="✅ Я оплатил", callback_data=NavCallback(action='paid', level='final').pack())
        await edit_or_send_message(callback, f"Вы выбрали: {callback_data.product} — {price}₽\n\nНажмите 'Перейти к оплате', а после вернитесь и нажмите 'Я оплатил'.", builder.as_markup())

@dp.callback_query(NavCallback.filter(F.action == 'paid'))
async def check_payment(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Проверяем вашу оплату..."); await asyncio.sleep(2)
    try:
        with open(PRODUCT_FILE, 'r', encoding='utf-8') as f: product_data = f.read()
        await callback.message.edit_text("✅ Оплата прошла успешно! Ваш товар:"); await callback.message.answer(product_data)
    except FileNotFoundError: logger.error(f"Файл товара {PRODUCT_FILE} не найден!"); await callback.message.edit_text("❌ Ошибка при выдаче товара. Обратитесь в поддержку.")
    await callback.answer()

# --- Запуск бота ---
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Бот запускается..."); asyncio.run(main())
