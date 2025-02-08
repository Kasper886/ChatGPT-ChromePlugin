import asyncio
import logging
import openai
import os
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
from models_list import AVAILABLE_MODELS  # Импорт списка моделей

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Файл для сохранения выбранной модели
SELECTED_MODEL_FILE = "selected_model.txt"
DEFAULT_MODEL = "gpt-3.5-turbo"

# Логирование
logging.basicConfig(level=logging.INFO)

def save_selected_model(model_name):
    try:
        with open(SELECTED_MODEL_FILE, "w") as f:
            f.write(model_name)
        logging.info(f"✅ Model saved: {model_name}")
    except Exception as e:
        logging.error(f"❌ Error saving model: {e}")

def load_selected_model():
    try:
        if os.path.exists(SELECTED_MODEL_FILE):
            with open(SELECTED_MODEL_FILE, "r") as f:
                model = f.read().strip()
                if model in AVAILABLE_MODELS:
                    return model
        return DEFAULT_MODEL
    except Exception as e:
        logging.error(f"❌ Error loading model: {e}")
        return DEFAULT_MODEL

selected_model = load_selected_model()

async def chat_with_gpt(user_message: str) -> str:
    try:
        selected_model = load_selected_model()
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"❌ ERROR in chat_with_gpt: {str(e)}")
        return f"Error: {str(e)}"

async def start_command(message: Message):
    await message.answer("Hello! Use /setmodel to choose a model.")

async def current_model(message: Message):
    selected_model = load_selected_model()
    await message.answer(f"🛠 Current model: {selected_model}")

async def set_model_command(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=model, callback_data=f"setmodel_{model}")]
            for model in AVAILABLE_MODELS
        ]
    )
    await message.answer("Select a model:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("setmodel_"))
async def process_model_selection(callback_query: types.CallbackQuery):
    model_name = callback_query.data.split("setmodel_")[1]
    if model_name in AVAILABLE_MODELS:
        save_selected_model(model_name)
        await callback_query.message.edit_text(f"✅ Model changed to: {model_name}")
    else:
        await callback_query.answer("Invalid model selection.", show_alert=True)

@dp.message()
async def handle_message(message: Message):
    response = await chat_with_gpt(message.text)
    await message.answer(response)

# Регистрация команд
dp.message.register(start_command, Command("start"))
dp.message.register(current_model, Command("currentmodel"))
dp.message.register(set_model_command, Command("setmodel"))

dp.message.register(handle_message)

async def main():
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())