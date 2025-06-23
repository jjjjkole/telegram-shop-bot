import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import json
import os
from datetime import datetime

BOT_TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_IDS = [5206914915]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

data_file = "data.json"
orders_file = "orders.txt"
products_file = "101.txt"

def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"cities": {}, "current": {}}

def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🛒 Каталог"))
    kb.add(KeyboardButton("📦 Получить товар"))
    kb.add(KeyboardButton("➕ Добавить товар"), KeyboardButton("➖ Удалить товар"))
    kb.add(KeyboardButton("🌆 Добавить город"), KeyboardButton("📂 Добавить категорию"))
    return kb

def get_city_keyboard(data):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for city in data.get("cities", {}):
        kb.add(KeyboardButton(city))
    return kb

def get_category_keyboard(data, city):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    categories = data.get("cities", {}).get(city, {})
    for category in categories:
        kb.add(KeyboardButton(category))
    return kb

def get_product_keyboard(data, city, category):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    products = data.get("cities", {}).get(city, {}).get(category, [])
    for product in products:
        kb.add(KeyboardButton(product))
    return kb

@dp.message()
async def handle_message(message: Message):
    text = message.text.strip()
    data = load_data()

    if text == "/start":
        await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard())

    elif text == "🛒 Каталог":
        await message.answer("Выберите город:", reply_markup=get_city_keyboard(data))

    elif text in data.get("cities", {}):
        data["current"][str(message.from_user.id)] = {"city": text}
        save_data(data)
        await message.answer("Выберите категорию:", reply_markup=get_category_keyboard(data, text))

    elif any(text in data.get("cities", {}).get(user_data.get("city", ""), {}) for user_data in [data.get("current", {}).get(str(message.from_user.id), {})]):
        user_data = data["current"].get(str(message.from_user.id), {})
        user_data["category"] = text
        data["current"][str(message.from_user.id)] = user_data
        save_data(data)
        await message.answer("Выберите товар:", reply_markup=get_product_keyboard(data, user_data["city"], text))

    elif text == "📦 Получить товар":
        content = "🔹 ТЕСТОВАЯ ВЫДАЧА:\n"
        first = ""
        if os.path.exists(products_file):
            with open(products_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                first = lines[0].strip()
                content += f"\n{first}"
                with open(products_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[1:])
            else:
                content += "\nТовары закончились."
        else:
            content += "\nФайл не найден."
        await message.answer(content)
        if first:
            with open(orders_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - {message.from_user.id} получил: {first}\n")

    elif text == "➕ Добавить товар" and message.from_user.id in ADMIN_IDS:
        await message.answer("Введите товар через команду: /add ваш_товар")

    elif text == "➖ Удалить товар" and message.from_user.id in ADMIN_IDS:
        await message.answer("Введите часть названия товара через: /del ключевое_слово")

    elif text == "🌆 Добавить город" and message.from_user.id in ADMIN_IDS:
        await message.answer("Введите город через команду: /addcity название")

    elif text == "📂 Добавить категорию" and message.from_user.id in ADMIN_IDS:
        await message.answer("Введите категорию через команду: /addcat название")

    elif text.startswith("/addcity ") and message.from_user.id in ADMIN_IDS:
        city = text[9:].strip()
        if city:
            data["cities"].setdefault(city, {})
            save_data(data)
            await message.answer(f"Город '{city}' добавлен ✅")

    elif text.startswith("/addcat ") and message.from_user.id in ADMIN_IDS:
        user_data = data.get("current", {}).get(str(message.from_user.id), {})
        city = user_data.get("city")
        if city:
            category = text[8:].strip()
            data["cities"].setdefault(city, {}).setdefault(category, [])
            save_data(data)
            await message.answer(f"Категория '{category}' добавлена в город '{city}' ✅")
        else:
            await message.answer("Сначала выбери город в /каталоге")

    elif text.startswith("/add ") and message.from_user.id in ADMIN_IDS:
        item = text[5:].strip()
        user_data = data.get("current", {}).get(str(message.from_user.id), {})
        city = user_data.get("city")
        category = user_data.get("category")
        if city and category and item:
            data["cities"].setdefault(city, {}).setdefault(category, []).append(item)
            save_data(data)
            await message.answer("Товар добавлен в выбранную категорию ✅")
        else:
            await message.answer("Выбери сначала город и категорию")

    elif text.startswith("/del ") and message.from_user.id in ADMIN_IDS:
        keyword = text[5:].strip()
        if os.path.exists(products_file):
            with open(products_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            lines = [line for line in lines if keyword not in line]
            with open(products_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
            await message.answer("Товары с таким содержимым удалены ✅")

    else:
        await message.answer("Неизвестная команда. Нажми /start или используй кнопки.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
