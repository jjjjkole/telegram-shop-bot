
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio
import json
import os

BOT_TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_IDS = [5206914915]
ADMIN_PASSWORD = "admin25"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
data_file = "data.json"

def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"products": [], "cities": [], "categories": []}

def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_main_keyboard(is_admin=False):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🛒 Каталог")
    if is_admin:
        builder.button(text="➕ Добавить товар")
        builder.button(text="➖ Удалить товар")
        builder.button(text="🏙️ Добавить город")
        builder.button(text="📂 Добавить категорию")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard(is_admin))

@dp.message(lambda msg: msg.text == "🛒 Каталог")
async def catalog_handler(message: types.Message):
    data = load_data()
    if not data["products"]:
        await message.answer("Каталог пуст.")
        return
    content = "📦 Каталог товаров:\n"
    for item in data["products"]:
        content += f"- {item['name']} ({item['price']}₽)\n"
    await message.answer(content)

@dp.message(lambda msg: msg.text == "➕ Добавить товар")
async def ask_add_product(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Введите товар в формате: Название - Цена")

@dp.message(lambda msg: "-" in msg.text and msg.from_user.id in ADMIN_IDS)
async def add_product(message: types.Message):
    data = load_data()
    try:
        name, price = map(str.strip, message.text.split("-"))
        price = int(price)
        data["products"].append({"name": name, "price": price})
        save_data(data)
        await message.answer("✅ Товар добавлен!")
    except Exception:
        await message.answer("❌ Ошибка! Используйте формат: Название - Цена")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
