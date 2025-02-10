import asyncio
import logging
import openai
import os
from datetime import datetime
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

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Global variable to track current chat file
current_chat_file = None

def create_new_chat_file():
    global current_chat_file
    timestamp = datetime.now().strftime("chat-%d-%m-%y-%H-%M-%S.txt")
    current_chat_file = timestamp
    with open(current_chat_file, "w") as f:
        f.write("Chat started\n")
    logging.info(f"New chat file created: {current_chat_file}")

def append_to_chat_file(text):
    if current_chat_file:
        with open(current_chat_file, "a") as f:
            f.write(text + "\n")

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
        # Проверяем, существует ли файл с историей чата
        if not current_chat_file or not os.path.exists(current_chat_file):
            await message.answer("❌ Please start a new chat with /startnewchat")
            return  # Завершаем выполнение функции
        
        user_message = message.text
        selected_model = load_selected_model()
        logging.info(f"📝 DEBUG: Sending request to ChatGPT with model: {selected_model} and message: {user_message}")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        messages = []
        if current_chat_file and os.path.exists(current_chat_file):
            with open(current_chat_file, "r") as f:
                for line in f:
                    if line.startswith("User:"):
                        messages.append({"role": "user", "content": line.replace("User: ", "").strip()})
                    elif line.startswith("Bot:"):
                        messages.append({"role": "assistant", "content": line.replace("Bot: ", "").strip()})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=selected_model,
            messages=messages
        )

        actual_model = response.model
        bot_response = response.choices[0].message.content

        logging.info(f"✅ DEBUG: Used model: {actual_model}")
        reply_text = f"(🔹 Real Model ID: {actual_model})\n{bot_response}"

        # Append conversation to chat file
        append_to_chat_file(f"User: {user_message}")
        append_to_chat_file(f"Bot: {bot_response}")

        await message.answer(reply_text)
    except Exception as e:
        logging.error(f"❌ ERROR in chat_with_gpt: {str(e)}")
        await message.answer(f"Error: {str(e)}")

async def start(message: Message):
    await message.answer(f"Please select a model with /setmodel (current model is gpt-3.5 turbo) and start a new chat with /startnewchat")

async def start_new_chat(message: Message):
    create_new_chat_file()
    timestamp = datetime.now().strftime("%d.%m.%Y %H.%M.%S")
    await message.answer(f"🆕 New session with ChatGPT {timestamp}")

async def current_model(message: Message):
    selected_model = load_selected_model()
    await message.answer(f"🛠 Current model: {selected_model}")

def set_model_command(message: Message):
    # Создаем список кнопок по 2 в ряд
    buttons = []
    row = []
    for i, model in enumerate(AVAILABLE_MODELS):
        row.append(InlineKeyboardButton(text=model, callback_data=f"setmodel_{model}"))
        if len(row) == 2 or i == len(AVAILABLE_MODELS) - 1:
            buttons.append(row)
            row = []

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return message.answer("Select a model:", reply_markup=keyboard)

async def model_selected(callback_query: types.CallbackQuery):
    model_name = callback_query.data.replace("setmodel_", "")
    if model_name in AVAILABLE_MODELS:
        save_selected_model(model_name)
        global selected_model
        selected_model = model_name
        await callback_query.message.edit_text(f"✅ Model changed to: {model_name}")
    else:
        await callback_query.answer("❌ Invalid model selection.", show_alert=True)

dp.message.register(start, Command("start"))
dp.message.register(start_new_chat, Command("startnewchat"))
dp.message.register(set_model_command, Command("setmodel"))
dp.message.register(current_model, Command("currentmodel"))
dp.callback_query.register(model_selected)
dp.message.register(chat_with_gpt)

async def main():
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())