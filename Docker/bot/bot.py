import asyncio
import logging
import openai
import os
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
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
async def start_command(message: Message):
    logging.info("✅ Received /start command")
    await message.answer("Hello! I am a bot connected to ChatGPT. Ask me anything!\n"
                         "To change the model, use /setmodel\n"
                         "To check the current model, use /currentmodel")

async def current_model(message: Message):
    logging.info("✅ Received /currentmodel command")
    selected_model = load_selected_model()
    await message.answer(f"🛠 The current model is: {selected_model}")

# Command to open model selection menu
async def select_model_menu(message: Message):
    logging.info("✅ Received /setmodel command")

    keyboard_buttons = [[KeyboardButton(text=f"/setmodel {model}")] for model in AVAILABLE_MODELS]
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer("Select a model:", reply_markup=keyboard)

# Function to change model when user selects from the menu
async def select_model(message: Message):
    logging.info(f"🔹 Received message: {message.text}")

    if message.text.startswith("/setmodel "):
        model_name = message.text.replace("/setmodel ", "").strip()

        if model_name in AVAILABLE_MODELS:
            save_selected_model(model_name)  # Сохраняем модель
            logging.info(f"✅ Model changed to: {model_name}")

            # Проверяем, сохранилась ли модель
            test_model = load_selected_model()
            logging.info(f"🔍 Loaded model after save: {test_model}")

            await message.answer(f"✅ Model changed to: {test_model}", reply_markup=ReplyKeyboardRemove())
        else:
            logging.warning(f"❌ Invalid model selected: {model_name}")
            await message.answer("❌ Invalid model selected. Use /setmodel to choose a model from the menu.")

# Function to interact with ChatGPT
async def chat_with_gpt(user_message: str) -> str:
    try:
        selected_model = load_selected_model()  # Load latest selected model
        client = openai.OpenAI()
        
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": user_message}]
        )

        actual_model = response.model  # Get the real model used
        logging.info(f"Used model: {actual_model}")

        return f"(🔹 Real Model ID: {actual_model})\n{response.choices[0].message.content}"
    except Exception as e:
        return f"Error: {str(e)}"

# Function to handle user messages
async def handle_message(message: Message):
    logging.info(f"🔹 Received user message: {message.text}")

    if message.text.startswith("/"):
        return  # Ignore unknown commands

    response = await chat_with_gpt(message.text)
    await message.answer(response)

# Register commands AFTER defining them
dp.message.register(start_command, Command("start"))
dp.message.register(select_model_menu, Command("setmodel"))
dp.message.register(current_model, Command("currentmodel"))
dp.message.register(select_model, lambda message: message.text.startswith("/setmodel "))  # Гарантируем вызов обработчика
dp.message.register(handle_message)  # Обработчик всех остальных сообщений

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