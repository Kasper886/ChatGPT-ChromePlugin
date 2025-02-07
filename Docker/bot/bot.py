import asyncio
import logging
import openai
import os
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from dotenv import load_dotenv
from models_list import AVAILABLE_MODELS  # Import available models from an external file

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()
app = Flask(__name__)

openai.api_key = OPENAI_API_KEY

# File to store the selected model persistently
SELECTED_MODEL_FILE = "selected_model.txt"
DEFAULT_MODEL = "gpt-3.5-turbo"  # Default model if no file exists

# Function to save the selected model to a file
def save_selected_model(model_name):
    with open(SELECTED_MODEL_FILE, "w") as f:
        f.write(model_name)

# Function to load the selected model from a file
def load_selected_model():
    if os.path.exists(SELECTED_MODEL_FILE):
        with open(SELECTED_MODEL_FILE, "r") as f:
            model = f.read().strip()
            if model in AVAILABLE_MODELS:
                return model
    return DEFAULT_MODEL  # Return default model if no valid file exists

# Load the last selected model from the file on startup
selected_model = load_selected_model()

# Command handlers
@router.message(Command("start"))
async def start_command(message: Message):
    logging.info("✅ Received /start command")
    await message.answer("Hello! I am a bot connected to ChatGPT. Ask me anything!\n"
                         "To change the model, use /selectmodel\n"
                         "To check the current model, use /currentmodel")
    
@router.message(Command("setmodel"))
async def select_model_menu(message: Message):
    logging.info("✅ Received /setmodel command")
    
    keyboard_buttons = [[KeyboardButton(text=model)] for model in AVAILABLE_MODELS]
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer("Select a model:", reply_markup=keyboard)

@router.message(Command("currentmodel"))
async def current_model(message: Message):
    logging.info("✅ Received /currentmodel command")
    selected_model = load_selected_model()
    await message.answer(f"🛠 The current model is: {selected_model}")

@router.message()
async def handle_message(message: Message):
    if message.text.startswith("/"):
        return  # Ignore unknown commands
    response = await chat_with_gpt(message.text)
    await message.answer(response)

# Register commands AFTER defining them
dp.include_router(router)

# Flask webhook for Google Meet
@app.route("/meet_webhook", methods=["POST"])
async def meet_webhook():
    data = request.json
    if "text" in data:
        user_message = data["text"]
        response = await chat_with_gpt(user_message)
        await send_telegram_message(response)
    return jsonify({"status": "ok"})

# Function to send a message to Telegram
async def send_telegram_message(text: str):
    await bot.send_message(os.getenv("TELEGRAM_CHAT_ID"), text)

# Function to run Flask in asyncio
def run_flask():
    app.run(host="0.0.0.0", port=5000, use_reloader=False)

# Main function
async def main():
    logging.info("Starting bot...")

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, run_flask)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())