import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
import json
import os
from datetime import datetime

BOT_TOKEN = "7710092707:AAH_Ae_pXuaFeePDgkm0zS8KfA3_GBz6H9w"

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

@dp.message()
async def handle_message(message: Message):
    if message.text == "/start":
        await message.answer("Привет! Выберите команду или товар.")
    elif message.text.startswith("/get_test"):
        content = "🔹 ТЕСТОВАЯ ВЫДАЧА:\n"
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
        with open(orders_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} - {message.from_user.id} получил: {first}\n")
    else:
        await message.answer("Неизвестная команда")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
