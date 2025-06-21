
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = '7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w'
ADMIN_ID = 5206914915

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

USER_STATE = {}

# FSM для добавления
class AdminState(StatesGroup):
    waiting_for_city = State()
    waiting_for_category_city = State()
    waiting_for_category_name = State()
    waiting_for_product_city = State()
    waiting_for_product_category = State()
    waiting_for_product_data = State()

def load_data():
    with open("bot/data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open("bot/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить город"))
    kb.add(KeyboardButton("➕ Добавить категорию"))
    kb.add(KeyboardButton("➕ Добавить товар"))
    kb.add(KeyboardButton("📋 Показать все"))
    await message.answer("🔧 Админ-панель:", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "➕ Добавить город")
async def add_city_start(message: types.Message):
    await message.answer("🏙 Введите название нового города:")
    await AdminState.waiting_for_city.set()

@dp.message_handler(state=AdminState.waiting_for_city)
async def add_city_finish(message: types.Message, state: FSMContext):
    data = load_data()
    city = message.text
    if city not in data:
        data[city] = {}
        save_data(data)
        await message.answer(f"✅ Город '{city}' добавлен.")
    else:
        await message.answer("⚠️ Такой город уже есть.")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "➕ Добавить категорию")
async def add_category_city(message: types.Message):
    await message.answer("🏙 Введите город, в который добавить категорию:")
    await AdminState.waiting_for_category_city.set()

@dp.message_handler(state=AdminState.waiting_for_category_city)
async def add_category_name(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("📂 Введите название новой категории:")
    await AdminState.waiting_for_category_name.set()

@dp.message_handler(state=AdminState.waiting_for_category_name)
async def add_category_finish(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    city = user_data['city']
    category = message.text
    data = load_data()
    if city in data:
        if category not in data[city]:
            data[city][category] = []
            save_data(data)
            await message.answer(f"✅ Категория '{category}' добавлена в '{city}'.")
        else:
            await message.answer("⚠️ Такая категория уже есть.")
    else:
        await message.answer("❌ Такого города нет.")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "➕ Добавить товар")
async def add_product_start(message: types.Message):
    await message.answer("🏙 Введите город для товара:")
    await AdminState.waiting_for_product_city.set()

@dp.message_handler(state=AdminState.waiting_for_product_city)
async def add_product_category(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("📂 Введите категорию:")
    await AdminState.waiting_for_product_category.set()

@dp.message_handler(state=AdminState.waiting_for_product_category)
async def add_product_data(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("🛒 Введите товар в формате:
Название | Цена | Описание")
    await AdminState.waiting_for_product_data.set()

@dp.message_handler(state=AdminState.waiting_for_product_data)
async def save_product(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        city = user_data['city']
        category = user_data['category']
        name, price, desc = [x.strip() for x in message.text.split("|")]
        product_id = str(hash(name + price) % 100000)
        data = load_data()
        if city in data and category in data[city]:
            data[city][category].append({
                "name": name,
                "price": price,
                "desc": desc,
                "product_id": product_id
            })
            save_data(data)
            await message.answer(f"✅ Товар '{name}' добавлен.")
        else:
            await message.answer("⚠️ Сначала добавьте город и категорию.")
    except:
        await message.answer("❌ Неверный формат.")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "📋 Показать все")
async def show_all_data(message: types.Message):
    data = load_data()
    response = ""
    for city, cats in data.items():
        response += f"🏙 {city}:
"
        for cat, products in cats.items():
            response += f"  📂 {cat}:
"
            for p in products:
                response += f"    - {p['name']} ({p['price']})
"
    await message.answer(response or "📭 Пусто.")
