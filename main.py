import json, os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from datetime import datetime

API_TOKEN = '7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w'
ADMIN_ID = 5206914915

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class AdminState(StatesGroup):
    waiting_for_city = State()
    waiting_for_category_city = State()
    waiting_for_category_name = State()
    waiting_for_product_city = State()
    waiting_for_product_category = State()
    waiting_for_product_data = State()
    waiting_for_deletion_city = State()
    waiting_for_deletion_category = State()
    waiting_for_deletion_product = State()

def load_data():
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    args = message.get_args()
    if args.startswith("paid_"):
        parts = args.split("_")
        if len(parts) == 3:
            product_id, user_id = parts[1], parts[2]
            if str(message.from_user.id) == user_id:
                data = load_data()
                for city, cats in data.items():
                    for cat, items in cats.items():
                        for product in items:
                            if product["product_id"] == product_id:
                                content = product.get("delivery", "")
                                fname = f"{product_id}.txt"
                                if os.path.exists(fname):
                                    with open(fname, "r+", encoding="utf-8") as f:
                                        lines = f.readlines()
                                        if lines:
                                            code = lines[0].strip()
                                            content = f"🔹 ТЕСТОВАЯ ВЫДАЧА:
{code}"
                                            f.seek(0)
                                            f.writelines(lines[1:])
                                            f.truncate()
                                        else:
                                            content = "⛔ Товар закончился."
                                with open("purchases.log", "a", encoding="utf-8") as log:
                                    log.write(f"{datetime.now()} - User: {user_id}, Product: {product_id}, City: {city}\n")
                                await message.answer(f"✅ Оплата подтверждена!\n\n{content}")
                                return
                await message.answer("⚠️ Товар не найден.")
                return
            else:
                await message.answer("⚠️ Ошибка идентификатора пользователя.")
                return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for city in load_data().keys():
        kb.add(KeyboardButton(city))
    await message.answer("🏙 Выберите город:", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text in load_data().keys())
async def choose_category(message: types.Message):
    city = message.text
    data = load_data()
    if city in data:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for cat in data[city].keys():
            kb.add(KeyboardButton(f"{city} >> {cat}"))
        await message.answer(f"📂 Категории в {city}:", reply_markup=kb)

@dp.message_handler(lambda msg: ">>" in msg.text)
async def show_products(message: types.Message):
    try:
        city, cat = [x.strip() for x in message.text.split(">>")]
        data = load_data()
        products = data[city][cat]
        for product in products:
            text = f"🛒 {product['name']}
💸 {product['price']}
ℹ️ {product['desc']}"
            pay_link = f"https://wondrous-choux-1cf04f.netlify.app/?product_id={product['product_id']}&user_id={message.from_user.id}&city={city}"
            btn = InlineKeyboardMarkup()
            btn.add(InlineKeyboardButton("💳 Перейти к оплате", url=pay_link))
            await message.answer(text, reply_markup=btn)
    except:
        await message.answer("⚠️ Ошибка отображения товара.")

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить город"))
    kb.add(KeyboardButton("➕ Добавить категорию"))
    kb.add(KeyboardButton("➕ Добавить товар"))
    kb.add(KeyboardButton("➖ Удалить товар"))
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
    await message.answer("🏙 Введите город:")
    await AdminState.waiting_for_product_city.set()

@dp.message_handler(state=AdminState.waiting_for_product_city)
async def add_product_category(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("📂 Введите категорию:")
    await AdminState.waiting_for_product_category.set()

@dp.message_handler(state=AdminState.waiting_for_product_category)
async def add_product_data(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("🛒 Введите товар:
Название | Цена | Описание | Delivery")
    await AdminState.waiting_for_product_data.set()

@dp.message_handler(state=AdminState.waiting_for_product_data)
async def save_product(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        city = user_data['city']
        category = user_data['category']
        name, price, desc, delivery = [x.strip() for x in message.text.split("|")]
        product_id = str(hash(name + price) % 100000)
        data = load_data()
        if city in data and category in data[city]:
            data[city][category].append({
                "name": name,
                "price": price,
                "desc": desc,
                "product_id": product_id,
                "delivery": delivery
            })
            with open(f"{product_id}.txt", "w", encoding="utf-8") as f:
                f.write("TEST-CODE-1234\nTEST-CODE-5678\n")
            save_data(data)
            await message.answer(f"✅ Товар '{name}' добавлен.")
        else:
            await message.answer("⚠️ Сначала добавьте город и категорию.")
    except:
        await message.answer("❌ Неверный формат.")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "➖ Удалить товар")
async def delete_start(message: types.Message):
    await message.answer("🏙 Введите город:")
    await AdminState.waiting_for_deletion_city.set()

@dp.message_handler(state=AdminState.waiting_for_deletion_city)
async def delete_category(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("📂 Введите категорию:")
    await AdminState.waiting_for_deletion_category.set()

@dp.message_handler(state=AdminState.waiting_for_deletion_category)
async def delete_product(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("🛒 Введите точное название товара для удаления:")
    await AdminState.waiting_for_deletion_product.set()

@dp.message_handler(state=AdminState.waiting_for_deletion_product)
async def delete_finish(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    name = message.text
    data = load_data()
    city = user_data['city']
    cat = user_data['category']
    if city in data and cat in data[city]:
        original = len(data[city][cat])
        data[city][cat] = [p for p in data[city][cat] if p['name'] != name]
        save_data(data)
        await message.answer(f"🗑 Удалено: {original - len(data[city][cat])}")
    else:
        await message.answer("❌ Город или категория не найдены.")
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

if __name__ == '__main__':
    executor.start_polling(dp)