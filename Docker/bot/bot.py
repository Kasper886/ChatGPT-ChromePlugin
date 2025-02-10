import asyncio
import logging
import openai
import os
from datetime import datetime
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ContentType, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
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
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Global variable to track current chat file
current_chat_file = None


# ==== UTILITY FUNCTIONS ====
def create_new_chat_file():
    """
    Creates a new chat log file with a timestamp.
    """
    global current_chat_file
    timestamp = datetime.now().strftime("chat-%d-%m-%y-%H-%M-%S.txt")
    current_chat_file = timestamp
    with open(current_chat_file, "w") as f:
        f.write("Chat started\n")
    logging.info(f"New chat file created: {current_chat_file}")


def append_to_chat_file(text):
    """
    Appends text to the chat log file.
    """
    if current_chat_file:
        with open(current_chat_file, "a") as f:
            f.write(text + "\n")


def save_selected_model(model_name):
    """
    Saves the selected model to a file.
    """
    try:
        with open(SELECTED_MODEL_FILE, "w") as f:
            f.write(model_name)
        logging.info(f"✅ Model {model_name} saved.")
    except Exception as e:
        logging.error(f"❌ Error saving model: {str(e)}")


def load_selected_model():
    """
    Loads the selected model from a file.
    """
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


def clean_message(text: str) -> str:
    """
    Cleans the input message by removing unnecessary phrases
    or unwanted content like "Голосовое сообщение".
    """
    if not text:  # If the text is None or empty
        return ""

    # Remove unwanted phrases
    unwanted_phrases = [
        "Голосовое сообщение",
        "Voice message",
        "Аудиосообщение",
        "Audio message",
    ]
    for phrase in unwanted_phrases:
        text = text.replace(phrase, "").strip()

    return text if text else ""


# ==== BOT HANDLERS ====
async def chat_with_gpt(message: Message):
    """
    Processes a user's message and generates a response using OpenAI's API.
    """
    try:
        # Log incoming messages
        logging.info(f"📝 DEBUG: Full message object: {message}")
        logging.info(f"📝 DEBUG: Chat type: {message.chat.type}")
        logging.info(f"📝 DEBUG: Original text: {message.text}")

        # Clean and prepare the message
        user_message = clean_message(message.text)
        logging.info(f"📝 DEBUG: Cleaned message: {user_message}")

        if not user_message:  # Ignore empty messages after cleaning
            await message.reply("❌ Сообщение не содержит текста для обработки.")
            return

        # Check if the chat file exists
        if not current_chat_file or not os.path.exists(current_chat_file):
            await message.reply("❌ Используйте /startnewchat для начала нового чата.")
            return

        # Load selected model
        selected_model = load_selected_model()
        logging.info(f"🤖 Using model: {selected_model}")

        # Load the chat history
        messages = []
        if current_chat_file and os.path.exists(current_chat_file):
            with open(current_chat_file, "r") as f:
                for line in f:
                    if line.startswith("User:"):
                        content = clean_message(line.replace("User: ", "").strip())
                        if content:
                            messages.append({"role": "user", "content": content})
                    elif line.startswith("Bot:"):
                        content = line.replace("Bot: ", "").strip()
                        if content:
                            messages.append({"role": "assistant", "content": content})

        # Add the new message to the conversation
        messages.append({"role": "user", "content": user_message})

        # Call OpenAI API
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages
        )

        actual_model = response.model
        bot_response = response.choices[0].message.content

        # Format the reply
        reply_text = f"(🔹 Model: {actual_model})\n{bot_response}"

        # Save the chat to the file
        append_to_chat_file(f"User: {user_message}")
        append_to_chat_file(f"Bot: {bot_response}")

        # Send the response
        await message.reply(reply_text)

    except Exception as e:
        logging.error(f"❌ Error in chat_with_gpt: {str(e)}")
        await message.reply(f"Произошла ошибка: {str(e)}")


@dp.message(Command("startnewchat"))
async def start_new_chat(message: Message):
    """
    Starts a new chat session by creating a new log file.
    """
    create_new_chat_file()
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    await message.reply(f"🆕 Новый чат начат: {timestamp}")


@dp.message(ContentType.TEXT)
async def handle_messages(message: Message):
    """
    Routes text messages to chat_with_gpt and handles non-text content.
    """
    if message.text.startswith("/"):
        logging.info(f"🔧 Command received: {message.text}")
        return  # Ignore commands here, they will be handled separately

    await chat_with_gpt(message)


@dp.message()
async def handle_non_text_messages(message: Message):
    """
    Handles non-text messages such as voice, photo, etc.
    """
    logging.info(f"📌 Received non-text content: {message.content_type}")
    await message.reply("❌ Этот тип сообщений не поддерживается. Отправьте текст.")


async def main():
    logging.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())