import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardRemove
import json
import os

BOT_TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"
ADMIN_IDS = [5206914915]
ADMIN_PASSWORD = "admin25"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

data_file = "data.json"
orders_file = "orders.txt"

def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"cities": {}, "admins": []}

def save_data(data):
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Добавить город"), KeyboardButton(text="📍 Удалить город")],
            [KeyboardButton(text="📂 Добавить категорию"), KeyboardButton(text="📂 Удалить категорию")],
            [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="➖ Удалить товар")],
            [KeyboardButton(text="📦 Каталог")]
        ],
        resize_keyboard=True
    )

def get_main_keyboard(is_admin=False):
    keyboard = [[KeyboardButton(text="📦 Каталог")]]
    if is_admin:
        keyboard.append([
            KeyboardButton(text="➕ Добавить товар"),
            KeyboardButton(text="➖ Удалить товар")
        ])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@dp.message()
async def handle_message(message: Message):
    text = message.text.strip()
    data = load_data()
    is_admin = message.from_user.id in data.get("admins", []) or message.from_user.id in ADMIN_IDS

    if text == "/start":
        await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard(is_admin=is_admin))

    elif text == "/admin":
        await message.answer("Введите пароль для входа в админку:")

    elif text == ADMIN_PASSWORD:
        if message.from_user.id not in data["admins"]:
            data["admins"].append(message.from_user.id)
            save_data(data)
        await message.answer("✅ Доступ в админку получен.", reply_markup=get_admin_keyboard())

    elif is_admin and text == "📍 Добавить город":
        await message.answer("Введите название города в формате: /add_city Город")

    elif is_admin and text.startswith("/add_city "):
        city = text.replace("/add_city ", "").strip()
        if city:
            data["cities"].setdefault(city, {})
            save_data(data)
            await message.answer(f"Город '{city}' добавлен ✅")

    elif is_admin and text == "📍 Удалить город":
        await message.answer("Введите название города для удаления в формате: /del_city Город")

    elif is_admin and text.startswith("/del_city "):
        city = text.replace("/del_city ", "").strip()
        if city in data["cities"]:
            del data["cities"][city]
            save_data(data)
            await message.answer(f"Город '{city}' удален ✅")
        else:
            await message.answer("Город не найден ❌")

    elif is_admin and text == "📂 Добавить категорию":
        await message.answer("Введите в формате: /add_cat Город Категория")

    elif is_admin and text.startswith("/add_cat "):
        try:
            _, city, category = text.split(maxsplit=2)
            data["cities"].setdefault(city, {}).setdefault(category, [])
            save_data(data)
            await message.answer(f"Категория '{category}' добавлена в город '{city}' ✅")
        except:
            await message.answer("Ошибка! Проверь формат: /add_cat Город Категория")

    elif is_admin and text == "📂 Удалить категорию":
        await message.answer("Введите в формате: /del_cat Город Категория")

    elif is_admin and text.startswith("/del_cat "):
        try:
            _, city, category = text.split(maxsplit=2)
            if city in data["cities"] and category in data["cities"][city]:
                del data["cities"][city][category]
                save_data(data)
                await message.answer(f"Категория '{category}' удалена из '{city}' ✅")
            else:
                await message.answer("Категория не найдена ❌")
        except:
            await message.answer("Ошибка! Проверь формат: /del_cat Город Категория")

    elif is_admin and text == "➕ Добавить товар":
        await message.answer("Введите в формате: /add_item Город Категория Товар")

    elif is_admin and text.startswith("/add_item "):
        try:
            _, city, category, item = text.split(maxsplit=3)
            data["cities"].setdefault(city, {}).setdefault(category, []).append(item)
            save_data(data)
            await message.answer("✅ Товар добавлен")
        except:
            await message.answer("Ошибка! Проверь формат: /add_item Город Категория Товар")

    elif is_admin and text == "➖ Удалить товар":
        await message.answer("Введите в формате: /del_item Город Категория Товар")

    elif is_admin and text.startswith("/del_item "):
        try:
            _, city, category, item = text.split(maxsplit=3)
            if item in data["cities"].get(city, {}).get(category, []):
                data["cities"][city][category].remove(item)
                save_data(data)
                await message.answer("✅ Товар удален")
            else:
                await message.answer("Товар не найден ❌")
        except:
            await message.answer("Ошибка! Проверь формат: /del_item Город Категория Товар")

    elif text == "📦 Каталог":
        content = "📦 Каталог товаров:
"
        for city, categories in data["cities"].items():
            content += f"
🏙️ {city}:
"
            for cat, items in categories.items():
                content += f"  📂 {cat}:
"
                for item in items:
                    content += f"    └ {item}
"
        await message.answer(content or "Каталог пуст.")

    else:
        await message.answer("Неизвестная команда. Нажми /start или используй кнопки.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    data = load_data()
    is_admin = user_id in ADMIN_IDS

    if text == "/start":
        await message.answer("Привет! Выберите действие:", reply_markup=get_main_keyboard(is_admin=is_admin))
    elif text == "/admin":
        await message.answer("Введите пароль для входа в админку:")
        return

    elif text == "admin25":
        if user_id not in ADMIN_IDS:
            ADMIN_IDS.append(user_id)
        await message.answer("Добро пожаловать в админку ✅", reply_markup=get_admin_keyboard())
        return

    elif text == "📍 Добавить город" and is_admin:
        await message.answer("Введите название города:")
        return

    elif text == "📂 Добавить категорию" and is_admin:
        await message.answer("Введите название категории:")
        return

    elif text == "➕ Добавить товар" and is_admin:
        await message.answer("Введите товар в формате: Название - Цена")
        return

    elif "-" in text and is_admin:
        parts = text.split("-")
        if len(parts) == 2:
            name = parts[0].strip()
            price = parts[1].strip()
            if "products" not in data:
                data["products"] = []
            data["products"].append({"name": name, "price": price})
            save_data(data)
            await message.answer("✅ Товар добавлен!")
        return

    elif text == "📦 Каталог":
        if "products" not in data or not data["products"]:
            await message.answer("Каталог пуст.")
        else:
            content = "📦 Каталог товаров:
"
            for item in data["products"]:
                content += f"- {item['name']} ({item['price']}₽)
"
            await message.answer(content)
        return

    else:
        await message.answer("Неизвестная команда. Нажми /start или используй кнопки.")

