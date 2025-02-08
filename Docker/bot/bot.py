import asyncio
import logging
import openai
import os
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
from models_list import AVAILABLE_MODELS  # Import available models from an external file

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

openai.api_key = OPENAI_API_KEY

# File to store the selected model persistently
SELECTED_MODEL_FILE = "selected_model.txt"
DEFAULT_MODEL = "gpt-3.5-turbo"  # Default model if no file exists

# Configure logging
logging.basicConfig(level=logging.INFO)

def save_selected_model(model_name):
    try:
        with open(SELECTED_MODEL_FILE, "w") as f:
            f.write(model_name)
        logging.info(f"✅ Model {model_name} saved.")
    except Exception as e:
        logging.error(f"❌ Error saving model: {str(e)}")

def load_selected_model():
    try:
        if os.path.exists(SELECTED_MODEL_FILE):
            with open(SELECTED_MODEL_FILE, "r") as f:
                model = f.read().strip()
                if model in AVAILABLE_MODELS:
                    return model
        return DEFAULT_MODEL
    except Exception as e:
        logging.error(f"❌ Error loading model: {str(e)}")
        return DEFAULT_MODEL

selected_model = load_selected_model()

async def chat_with_gpt(message: Message):
    try:
        user_message = message.text
        selected_model = load_selected_model()
        logging.info(f"📝 DEBUG: Sending request to ChatGPT with model: {selected_model} and message: {user_message}")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": user_message}]
        )

        actual_model = response.model
        logging.info(f"✅ DEBUG: Used model: {actual_model}")

        reply_text = f"(🔹 Real Model ID: {actual_model})\n{response.choices[0].message.content}"
        await message.answer(reply_text)
    except Exception as e:
        logging.error(f"❌ ERROR in chat_with_gpt: {str(e)}")
        await message.answer(f"Error: {str(e)}")

async def start_command(message: Message):
    await message.answer("Hello! Use /setmodel to select a model.")

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

@dp.callback_query()
async def model_selected(callback_query: types.CallbackQuery):
    model_name = callback_query.data.replace("setmodel_", "")
    if model_name in AVAILABLE_MODELS:
        save_selected_model(model_name)
        global selected_model
        selected_model = model_name
        await callback_query.message.edit_text(f"✅ Model changed to: {model_name}")
    else:
        await callback_query.answer("❌ Invalid model selection.", show_alert=True)

dp.message.register(start_command, Command("start"))
dp.message.register(current_model, Command("currentmodel"))
dp.message.register(set_model_command, Command("setmodel"))

dp.callback_query.register(model_selected)

dp.message.register(chat_with_gpt)

async def main():
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())