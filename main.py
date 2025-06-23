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

admin_authenticated = set()

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Каталог")],
            [KeyboardButton(text="📦 Получить товар")],
            [KeyboardButton(text="Админка")]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="➖ Удалить товар")],
            [KeyboardButton(text="⬅ Назад")]
        ],
        resize_keyboard=True
    )

@dp.message()
async def handle_message(message: Message):
    text = message.text.strip()

    if text == "/start":
        await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard())

    elif text == "Админка":
        await message.answer("Введите пароль для входа в админку:")

    elif text == ADMIN_PASSWORD:
        admin_authenticated.add(message.from_user.id)
        await message.answer("Вход в админку выполнен ✅", reply_markup=get_admin_keyboard())

    elif text == "⬅ Назад":
        if message.from_user.id in admin_authenticated:
            admin_authenticated.remove(message.from_user.id)
        await message.answer("Выход из админки.", reply_markup=get_main_keyboard())

    elif text == "📦 Получить товар":
        content = "🔹 ТЕСТОВАЯ ВЫДАЧА:
"
        first = ""
        if os.path.exists(products_file):
            with open(products_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                first = lines[0].strip()
                content += f"{first}"
                with open(products_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[1:])
            else:
                content += "Товары закончились."
        else:
            content += "Файл не найден."
        await message.answer(content)
        if first:
            with open(orders_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - {message.from_user.id} получил: {first}
")

    elif text == "➕ Добавить товар" and message.from_user.id in admin_authenticated:
        await message.answer("Введите товар через команду: /add ваш_товар")

    elif text == "➖ Удалить товар" and message.from_user.id in admin_authenticated:
        await message.answer("Введите часть названия товара через: /del ключевое_слово")

    elif text.startswith("/add ") and message.from_user.id in admin_authenticated:
        item = text[5:].strip()
        if item:
            with open(products_file, "a", encoding="utf-8") as f:
                f.write(f"{item}\n")
            await message.answer("Товар добавлен ✅")

    elif text.startswith("/del ") and message.from_user.id in admin_authenticated:
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