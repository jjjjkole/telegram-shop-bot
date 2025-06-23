
import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_IDS = [5206914915]
ADMIN_PASSWORD = "admin25"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

data_file = "data.json"
orders_file = "orders.txt"
products_file = "101.txt"

state = {}

def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"products": [], "cities": [], "categories": []}

def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_main_keyboard(is_admin=False):
    kb = [
        [KeyboardButton(text="🛒 Каталог")],
        [KeyboardButton(text="📦 Получить товар")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="➖ Удалить товар")])
        kb.append([KeyboardButton(text="🏙️ Добавить город"), KeyboardButton(text="📂 Добавить категорию")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(F.text == "/start")
async def start(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard(is_admin))

@dp.message(F.text == "/admin")
async def admin_login(message: Message):
    await message.answer("Введите пароль для входа в админку:", reply_markup=ReplyKeyboardRemove())
    state[message.from_user.id] = "awaiting_admin_password"

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if state.get(user_id) == "awaiting_admin_password":
        if text == ADMIN_PASSWORD:
            ADMIN_IDS.append(user_id)
            await message.answer("Успешный вход в админку ✅", reply_markup=get_main_keyboard(is_admin=True))
        else:
            await message.answer("Неверный пароль ❌")
        state[user_id] = None
        return

    if text == "📦 Получить товар":
        content = "🔹 ТЕСТОВАЯ ВЫДАЧА:"
        first = ""
        if os.path.exists(products_file):
            with open(products_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                first = lines[0].strip()
                content += f"
{first}"
                with open(products_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[1:])
            else:
                content += "
Товары закончились."
        else:
            content += "
Файл не найден."
        await message.answer(content)
        if first:
            with open(orders_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - {user_id} получил: {first}\n")

    elif text == "➕ Добавить товар" and user_id in ADMIN_IDS:
        await message.answer("Введите название товара:")
        state[user_id] = "add_product"

    elif text == "➖ Удалить товар" and user_id in ADMIN_IDS:
        await message.answer("Введите ключевое слово товара для удаления:")
        state[user_id] = "del_product"

    elif text == "🏙️ Добавить город" and user_id in ADMIN_IDS:
        await message.answer("Введите название города:")
        state[user_id] = "add_city"

    elif text == "📂 Добавить категорию" and user_id in ADMIN_IDS:
        await message.answer("Введите название категории:")
        state[user_id] = "add_category"

    elif state.get(user_id) == "add_product":
        with open(products_file, "a", encoding="utf-8") as f:
            f.write(f"{text}\n")
        await message.answer("Товар добавлен ✅")
        state[user_id] = None

    elif state.get(user_id) == "del_product":
        if os.path.exists(products_file):
            with open(products_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            lines = [line for line in lines if text not in line]
            with open(products_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
            await message.answer("Удаление завершено ✅")
        state[user_id] = None

    elif state.get(user_id) == "add_city":
        data = load_data()
        data["cities"].append(text)
        save_data(data)
        await message.answer("Город добавлен ✅")
        state[user_id] = None

    elif state.get(user_id) == "add_category":
        data = load_data()
        data["categories"].append(text)
        save_data(data)
        await message.answer("Категория добавлена ✅")
        state[user_id] = None

    else:
        await message.answer("Неизвестная команда. Нажми /start или используй кнопки.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
