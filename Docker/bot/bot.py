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

# Function to generate model selection keyboard
def get_model_keyboard():
    keyboard_buttons = [[KeyboardButton(text=model)] for model in AVAILABLE_MODELS]
    return ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Command to open model selection menu
@dp.message(Command("selectmodel"))
async def select_model_menu(message: Message):
    logging.info("✅ Received /selectmodel command")
    keyboard = get_model_keyboard()
    await message.answer("Select a model:", reply_markup=keyboard)

# Function to change the model when the user selects from the menu
@dp.message()
async def select_model(message: Message):
    global selected_model
    if message.text in AVAILABLE_MODELS:
        selected_model = message.text
        save_selected_model(selected_model)  # Save model to file
        await message.answer(f"✅ Model changed to: {selected_model}", reply_markup=ReplyKeyboardRemove())
    elif message.text.startswith("/"):
        return  # Ignore commands to avoid interference
    else:
        await message.answer("❌ Invalid model selected. Use /selectmodel to choose a model from the menu.")

# Function to check the current selected model
@dp.message(Command("currentmodel"))
async def current_model(message: Message):
    logging.info("✅ Received /currentmodel command")
    selected_model = load_selected_model()
    await message.answer(f"🛠 The current model is: {selected_model}")

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

        # Inject real model ID into response
        return f"(🔹 Real Model ID: {actual_model})\n{response.choices[0].message.content}"
    except Exception as e:
        return f"Error: {str(e)}"

# Telegram bot handlers
@dp.message(Command("start"))
async def start_command(message: Message):
    logging.info("✅ Received /start command")
    global selected_model
    selected_model = load_selected_model()  # Ensure model is loaded on start
    await message.answer("Hello! I am a bot connected to ChatGPT. Ask me anything!\n"
                         "To change the model, use /selectmodel\n"
                         "To check the current model, use /currentmodel")

@dp.message()
async def handle_message(message: Message):
    if message.text.startswith("/"):
        return  # Ignore unknown commands
    response = await chat_with_gpt(message.text)
    await message.answer(response)

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

# Main function to run both Flask and Telegram bot concurrently
async def main():
    logging.info("Starting bot...")

    # Принудительно регистрируем команды
    dp.message.register(start_command, Command("start"))
    dp.message.register(select_model_menu, Command("selectmodel"))
    dp.message.register(current_model, Command("currentmodel"))
    dp.message.register(handle_message)  # Handle general messages

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, run_flask)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())