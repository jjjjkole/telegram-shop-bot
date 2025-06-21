
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
import os

API_TOKEN = '7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w'
ADMIN_ID = 5206914915

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

USER_STATE = {}

def load_data():
    with open("bot/data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open("bot/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    
    if message.get_args().startswith("paid_"):
        args = message.get_args().split("_")
        product_id, user_id = args[1], args[2]
        if str(message.from_user.id) == user_id:
            data = load_data()
            found = None
            for city in data.values():
                for cat in city.values():
                    for product in cat:
                        if product["product_id"] == product_id:
                            found = product
                            break
            if found:
                await message.answer(f"✅ Оплата подтверждена!\n\n{found['delivery']}")
            else:
                await message.answer("⚠️ Товар не найден.")
        else:
            await message.answer("⚠️ Ошибка идентификатора пользователя.")
        return
    :
        args = message.get_args().split("_")
        product_id, user_id = args[1], args[2]
        if str(message.from_user.id) == user_id:
            await message.answer(f"✅ Оплата за товар {product_id} подтверждена. Админ скоро свяжется с вами.")
        else:
            await message.answer("⚠️ Ошибка идентификатора пользователя.")
        return

    data = load_data()
    cities = list(data.keys())
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for city in cities:
        keyboard.add(KeyboardButton(city))
    USER_STATE[message.from_user.id] = {}
    await message.answer("🏙 Выберите ваш город:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in load_data())
async def select_city(message: types.Message):
    city = message.text
    data = load_data()
    categories = list(data[city].keys())
    USER_STATE[message.from_user.id]["city"] = city

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in categories:
        keyboard.add(KeyboardButton(cat))
    keyboard.add(KeyboardButton("⬅ Назад"))
    await message.answer(f"📂 Вы выбрали город {city}. Теперь выберите категорию:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "⬅ Назад")
async def go_back(message: types.Message):
    await start_cmd(message)

@dp.message_handler()
async def select_category_or_product(message: types.Message):
    user_id = message.from_user.id
    if user_id not in USER_STATE or "city" not in USER_STATE[user_id]:
        return await start_cmd(message)

    city = USER_STATE[user_id]["city"]
    data = load_data()

    if message.text in data[city]:
        category = message.text
        USER_STATE[user_id]["category"] = category
        products = data[city][category]

        markup = InlineKeyboardMarkup()
        for item in products:
            btn = InlineKeyboardButton(
                text=f"{item['name']} — {item['price']}",
                callback_data=f"product_{item['product_id']}"
            )
            markup.add(btn)

        await message.answer(f"🛍 Товары в категории {category}:", reply_markup=markup)
    else:
        await message.answer("❌ Не понял категорию. Попробуйте снова.")

@dp.callback_query_handler(lambda call: call.data.startswith("product_"))
async def handle_product(call: types.CallbackQuery):
    product_id = call.data.split("_")[1]
    user_id = call.from_user.id
    state = USER_STATE.get(user_id, {})
    city = state.get("city", "неизвестно")

    pay_url = f"https://wondrous-choux-1cf04f.netlify.app/?product_id={product_id}&user_id={user_id}&city={city}"
    btn = InlineKeyboardMarkup().add(
        InlineKeyboardButton("💳 Перейти к оплате", url=pay_url)
    )

    await call.message.answer(f"💰 Нажмите кнопку ниже, чтобы перейти к оплате:", reply_markup=btn)

# ========== Админ-команды ==========
@dp.message_handler(commands=['add_city'])
async def add_city(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    try:
        city = message.text.split(maxsplit=1)[1]
        data = load_data()
        if city not in data:
            data[city] = {}
            save_data(data)
            await message.answer(f"✅ Город '{city}' добавлен.")
        else:
            await message.answer("⚠️ Такой город уже есть.")
    except:
        await message.answer("⚠️ Используй: /add_city <город>")

@dp.message_handler(commands=['add_category'])
async def add_category(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    try:
        _, city, category = message.text.split(maxsplit=2)
        data = load_data()
        if city in data:
            if category not in data[city]:
                data[city][category] = []
                save_data(data)
                await message.answer(f"✅ Категория '{category}' добавлена в '{city}'.")
            else:
                await message.answer("⚠️ Такая категория уже есть.")
        else:
            await message.answer("⚠️ Сначала добавь город.")
    except:
        await message.answer("⚠️ Используй: /add_category <город> <категория>")

@dp.message_handler(commands=['add_product'])
async def add_product(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    try:
        _, city, category, rest = message.text.split(maxsplit=3)
        name, price, desc = [s.strip() for s in rest.split('|')]
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
            await message.answer(f"✅ Товар '{name}' добавлен с ID {product_id}.")
        else:
            await message.answer("⚠️ Сначала добавь город и категорию.")
    except:
        await message.answer("⚠️ Используй: /add_product <город> <категория> Название | Цена | Описание")

@dp.message_handler(commands=['list_data'])
async def list_data(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    data = load_data()
    response = ""
    for city, categories in data.items():
        response += f"📍 {city}:
"
        for cat, products in categories.items():
            response += f"  🗂 {cat}:
"
            for p in products:
                response += f"    - {p['name']} ({p['price']}) [ID: {p['product_id']}]
"
    await message.answer(response or "📭 Данных пока нет.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
