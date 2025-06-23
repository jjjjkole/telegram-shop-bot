import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import json
import os
from datetime import datetime

BOT_TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_IDS = [5206914915]
ADMIN_PASSWORD = "admin25"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

data_file = "data.json"
orders_file = "orders.txt"
products_file = "101.txt"

def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"cities": [], "categories": [], "products": []}

def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_main_keyboard(is_admin=False):
    buttons = [
        [KeyboardButton(text="🛒 Каталог")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="➖ Удалить товар")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@dp.message()
async def handle_message(message: Message):
    text = message.text.strip()
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS

    if text == "/start":
        await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard(is_admin))

    elif text == "🛒 Каталог":
        data = load_data()
        if not data["products"]:
            await message.answer("Каталог пуст.")
        else:
            catalog = "\n".join(f"- {p}" for p in data["products"])
            await message.answer(f"📦 Каталог товаров:\n{catalog}")

    elif text == "➕ Добавить товар" and is_admin:
        await message.answer("Введите товар в формате: /add товар")

    elif text == "➖ Удалить товар" and is_admin:
        await message.answer("Введите часть названия для удаления: /del ключевое_слово")

    elif text.startswith("/add ") and is_admin:
        product = text[5:].strip()
        data = load_data()
        data["products"].append(product)
        save_data(data)
        await message.answer("✅ Товар добавлен!")

    elif text.startswith("/del ") and is_admin:
        keyword = text[5:].strip()
        data = load_data()
        before = len(data["products"])
        data["products"] = [p for p in data["products"] if keyword not in p]
        save_data(data)
        await message.answer(f"🗑️ Удалено: {before - len(data['products'])}")

    else:
        await message.answer("Неизвестная команда. Нажми /start или используй кнопки.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
