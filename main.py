import json
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import os

API_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "data.json"
ORDERS_FILE = "orders.txt"
STOCK_FILE = "101.txt"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"cities": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_stock():
    if not os.path.exists(STOCK_FILE):
        return []
    with open(STOCK_FILE, "r") as f:
        return f.read().splitlines()

def pop_stock():
    stock = get_stock()
    if stock:
        item = stock.pop(0)
        with open(STOCK_FILE, "w") as f:
            f.write("\n".join(stock))
        return item
    return None

def log_order(user_id, city, category, product):
    with open(ORDERS_FILE, "a") as f:
        f.write(f"{user_id} | {city} | {category} | {product}\n")

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    data = load_data()
    keyboard = InlineKeyboardMarkup()
    for city in data["cities"]:
        keyboard.add(InlineKeyboardButton(city, callback_data=f"city:{city}"))
    await message.answer("Выберите город:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("city:"))
async def choose_category(callback_query: types.CallbackQuery):
    city = callback_query.data.split(":")[1]
    data = load_data()
    keyboard = InlineKeyboardMarkup()
    for category in data["cities"][city]:
        keyboard.add(InlineKeyboardButton(category, callback_data=f"category:{city}:{category}"))
    await callback_query.message.edit_text("Выберите категорию:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("category:"))
async def choose_product(callback_query: types.CallbackQuery):
    _, city, category = callback_query.data.split(":")
    data = load_data()
    keyboard = InlineKeyboardMarkup()
    for product in data["cities"][city][category]:
        keyboard.add(InlineKeyboardButton(product, callback_data=f"product:{city}:{category}:{product}"))
    await callback_query.message.edit_text("Выберите товар:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("product:"))
async def send_product(callback_query: types.CallbackQuery):
    _, city, category, product = callback_query.data.split(":")
    stock_item = pop_stock()
    log_order(callback_query.from_user.id, city, category, product)
    content = f"🔹 ТЕСТОВАЯ ВЫДАЧА:\n\n📦 {stock_item if stock_item else 'Нет в наличии'}"
    await callback_query.message.edit_text(content)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
