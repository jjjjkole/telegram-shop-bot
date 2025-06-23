import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, KeyboardButton
from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
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
    return {}

def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Каталог")],
            [KeyboardButton(text="📦 Получить товар")],
            [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="➖ Удалить товар")],
            [KeyboardButton(text="➕ Добавить город"), KeyboardButton(text="➕ Добавить категорию")]
        ],
        resize_keyboard=True
    )

@dp.message()
async def handle_message(message: Message):
    text = message.text.strip()
    data = load_data()

    if text == "/start":
        await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard())

    elif text == "📦 Получить товар":
        content = "🔹 ТЕСТОВАЯ ВЫДАЧА:
"
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

    elif text == "🛒 Каталог":
        if not data:
            await message.answer("Каталог пуст.")
            return
        cities = list(data.keys())
        await message.answer("Выберите город:
" + "\n".join(cities))

    elif text.startswith("/addcity ") and message.from_user.id in ADMIN_IDS:
        city = text.replace("/addcity ", "").strip()
        if city not in data:
            data[city] = {}
            save_data(data)
            await message.answer(f"Город '{city}' добавлен ✅")
        else:
            await message.answer("Такой город уже есть.")

    elif text.startswith("/addcat ") and message.from_user.id in ADMIN_IDS:
        parts = text.split()
        if len(parts) >= 3:
            city = parts[1]
            cat = " ".join(parts[2:])
            if city in data:
                if cat not in data[city]:
                    data[city][cat] = []
                    save_data(data)
                    await message.answer(f"Категория '{cat}' в городе '{city}' добавлена ✅")
                else:
                    await message.answer("Такая категория уже есть.")
            else:
                await message.answer("Город не найден.")
        else:
            await message.answer("Формат: /addcat Город Категория")

    elif text == "➕ Добавить товар" and message.from_user.id in ADMIN_IDS:
        await message.answer("Введите товар через команду: /add ваш_товар")

    elif text == "➖ Удалить товар" and message.from_user.id in ADMIN_IDS:
        await message.answer("Введите часть названия товара через: /del ключевое_слово")

    elif text.startswith("/add ") and message.from_user.id in ADMIN_IDS:
        item = text[5:].strip()
        if item:
            with open(products_file, "a", encoding="utf-8") as f:
                f.write(f"{item}\n")
            await message.answer("Товар добавлен ✅")

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
