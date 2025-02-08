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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def save_selected_model(model_name):
    try:
        logging.info(f"📝 DEBUG: save_selected_model() called with model: {model_name}")

        # Проверяем, существует ли файл
        if not os.path.exists(SELECTED_MODEL_FILE):
            logging.warning(f"⚠ File {SELECTED_MODEL_FILE} not found, creating it...")
            with open(SELECTED_MODEL_FILE, "w") as f:
                f.write("")
            os.chmod(SELECTED_MODEL_FILE, 0o666)

        # Лог перед записью
        logging.info(f"📝 DEBUG: Writing model '{model_name}' to {SELECTED_MODEL_FILE}")

        # Записываем модель в файл
        with open(SELECTED_MODEL_FILE, "w") as f:
            f.write(model_name)
            f.flush()
            os.fsync(f.fileno())

        # Читаем файл обратно
        with open(SELECTED_MODEL_FILE, "r") as f:
            saved_model = f.read().strip()
            logging.info(f"📄 DEBUG: File content after save: {saved_model}")

        if saved_model != model_name:
            logging.error(f"❌ DEBUG: Model save mismatch! Expected: {model_name}, Found: {saved_model}")

    except Exception as e:
        logging.error(f"❌ DEBUG: Error saving model {model_name}: {str(e)}")

def load_selected_model():
    try:
        if os.path.exists(SELECTED_MODEL_FILE):
            with open(SELECTED_MODEL_FILE, "r") as f:
                model = f.read().strip()
                if model:
                    if model in AVAILABLE_MODELS:
                        logging.info(f"✅ Loaded selected model: {model}")
                        return model
                    else:
                        logging.warning(f"⚠ Model in file is invalid: {model}, using default.")
                else:
                    logging.warning(f"⚠ File exists but is empty, using default model: {DEFAULT_MODEL}")
        else:
            logging.warning(f"⚠ {SELECTED_MODEL_FILE} not found, using default model: {DEFAULT_MODEL}")
    except Exception as e:
        logging.error(f"❌ Error loading model from file: {str(e)}")
    return DEFAULT_MODEL

selected_model = load_selected_model()

async def chat_with_gpt(user_message: str) -> str:
    try:
        selected_model = load_selected_model()
        logging.info(f"📝 DEBUG: Sending request to ChatGPT with model: {selected_model} and message: {user_message}")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": user_message}]
        )

        actual_model = response.model
        logging.info(f"✅ DEBUG: Used model: {actual_model}")

        return f"(🔹 Real Model ID: {actual_model})\n{response.choices[0].message.content}"
    except Exception as e:
        logging.error(f"❌ ERROR in chat_with_gpt: {str(e)}")
        return f"Error: {str(e)}"

async def start_command(message: Message):
    logging.info("✅ Received /start command")
    await message.answer("Hello! I am a bot connected to ChatGPT. Ask me anything!\n"
                         "To change the model, use /setmodel\n"
                         "To check the current model, use /currentmodel")

async def current_model(message: Message):
    logging.info("✅ Received /currentmodel command")
    selected_model = load_selected_model()
    await message.answer(f"🛠 The current model is: {selected_model}")

async def select_model_menu(message: Message):
    logging.info("✅ Received /setmodel command")
    keyboard_buttons = [[KeyboardButton(text=f"/setmodel {model}")] for model in AVAILABLE_MODELS]
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Select a model:", reply_markup=keyboard)

async def select_model(message: Message):
    logging.info(f"🔹 DEBUG: Received /setmodel command with text: {message.text}")

    if message.text.startswith("/setmodel "):
        model_name = message.text.replace("/setmodel ", "").strip()
        logging.info(f"📝 DEBUG: Attempting to set model: {model_name}")

        if model_name in AVAILABLE_MODELS:
            logging.info(f"📝 DEBUG: {model_name} is in list")
            save_selected_model(model_name)
            global selected_model
            selected_model = model_name
            logging.info(f"✅ DEBUG: Model changed to: {selected_model}")
            await message.answer(f"✅ Model changed to: {selected_model}", reply_markup=ReplyKeyboardRemove())
        else:
            logging.warning(f"❌ DEBUG: Invalid model selected: {model_name}")
            await message.answer("❌ Invalid model selected. Use /setmodel to choose a model from the menu.")

dp.message.register(start_command, Command("start"))
dp.message.register(select_model_menu, Command("setmodel"))
dp.message.register(current_model, Command("currentmodel"))
dp.message.register(select_model, lambda message: message.text.startswith("/setmodel "))

@dp.message()
async def handle_message(message: Message):
    logging.info(f"🔹 DEBUG: Received user message: {message.text}")

    # Игнорируем команды
    if message.text.startswith("/"):
        logging.info(f"🚫 DEBUG: Ignoring command: {message.text}")
        return  

    response = await chat_with_gpt(message.text)
    await message.answer(response)

dp.message.register(handle_message)

async def main():
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())