import asyncio
import logging
import openai
import os
from datetime import datetime
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.enums import ContentType
from dotenv import load_dotenv
from models_list import AVAILABLE_MODELS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    # Load environment variables
    load_dotenv()

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY не найден в .env файле")

    # Initialize bot and dispatcher
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Configure OpenAI
    openai.api_key = OPENAI_API_KEY

    # Constants
    SELECTED_MODEL_FILE = "selected_model.txt"
    DEFAULT_MODEL = "gpt-3.5-turbo"

    # Global variables
    current_chat_file = None
    
except Exception as e:
    logger.error(f"Ошибка инициализации: {str(e)}")
    raise

# Вспомогательные функции
async def create_new_chat_file():
    try:
        global current_chat_file
        timestamp = datetime.now().strftime("chat-%d-%m-%y-%H-%M-%S.txt")
        current_chat_file = timestamp
        with open(current_chat_file, "w", encoding='utf-8') as f:
            f.write("Chat started\n")
        logger.info(f"New chat file created: {current_chat_file}")
    except Exception as e:
        logger.error(f"Ошибка создания файла чата: {str(e)}")
        raise

async def append_to_chat_file(text):
    try:
        if current_chat_file:
            with open(current_chat_file, "a", encoding='utf-8') as f:
                f.write(text + "\n")
    except Exception as e:
        logger.error(f"Ошибка записи в файл чата: {str(e)}")

async def save_selected_model(model_name):
    try:
        with open(SELECTED_MODEL_FILE, "w", encoding='utf-8') as f:
            f.write(model_name)
        logger.info(f"✅ Model {model_name} saved.")
    except Exception as e:
        logger.error(f"❌ Error saving model: {str(e)}")

async def load_selected_model():
    try:
        if os.path.exists(SELECTED_MODEL_FILE):
            with open(SELECTED_MODEL_FILE, "r", encoding='utf-8') as f:
                model = f.read().strip()
                if model in AVAILABLE_MODELS:
                    return model
        return DEFAULT_MODEL
    except Exception as e:
        logger.error(f"❌ Error loading model: {str(e)}")
        return DEFAULT_MODEL

def clean_message(text: str) -> str:
    if not text:
        return ""
    try:
        unwanted_phrases = [
            "Голосовое сообщение",
            "Voice message",
            "Аудиосообщение",
            "Audio message",
        ]
        for phrase in unwanted_phrases:
            text = text.replace(phrase, "").strip()
        return text if text else ""
    except Exception as e:
        logger.error(f"Ошибка очистки сообщения: {str(e)}")
        return ""

# Обработчики команд
@dp.message(CommandStart())
async def cmd_start(message: Message):
    try:
        await message.answer("Привет! Используйте /startnewchat для начала нового чата.")
    except Exception as e:
        logger.error(f"Ошибка в команде start: {str(e)}")

@dp.message(Command("startnewchat"))
async def start_new_chat(message: Message):
    try:
        await create_new_chat_file()
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        await message.answer(f"🆕 Новая сессия начата: {timestamp}")
    except Exception as e:
        logger.error(f"Ошибка в startnewchat: {str(e)}")
        await message.answer("❌ Ошибка при создании нового чата")

# Обработчик текстовых сообщений
async def chat_with_gpt(message: Message):
    try:
        logger.info(f"Входящее сообщение от {message.from_user.id}: {message.text}")

        if not message.text:
            await message.answer("❌ Пустое сообщение")
            return

        user_message = clean_message(message.text)
        if not user_message:
            await message.answer("❌ Сообщение не содержит текста для обработки")
            return

        if not current_chat_file or not os.path.exists(current_chat_file):
            await message.answer("❌ Начните новый чат командой /startnewchat")
            return

        selected_model = await load_selected_model()
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        messages = []
        try:
            with open(current_chat_file, "r", encoding='utf-8') as f:
                for line in f:
                    if line.startswith("User:"):
                        content = clean_message(line.replace("User: ", "").strip())
                        if content:
                            messages.append({"role": "user", "content": content})
                    elif line.startswith("Bot:"):
                        content = line.replace("Bot: ", "").strip()
                        if content:
                            messages.append({"role": "assistant", "content": content})
        except Exception as e:
            logger.error(f"Ошибка чтения истории чата: {str(e)}")
            messages = []

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=selected_model,
            messages=messages
        )

        bot_response = response.choices[0].message.content
        actual_model = response.model

        await append_to_chat_file(f"User: {user_message}")
        await append_to_chat_file(f"Bot: {bot_response}")

        await message.answer(f"(🔹 Model: {actual_model})\n{bot_response}")

    except Exception as e:
        logger.error(f"Ошибка в chat_with_gpt: {str(e)}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

# Общий обработчик сообщений
@dp.message()
async def handle_messages(message: Message):
    try:
        if message.content_type == ContentType.TEXT:
            if not message.text.startswith('/'):
                await chat_with_gpt(message)
        else:
            logger.info(f"Получено сообщение типа: {message.content_type}")
            await message.answer("❌ Поддерживаются только текстовые сообщения")
    except Exception as e:
        logger.error(f"Ошибка в handle_messages: {str(e)}")
        await message.answer("❌ Произошла ошибка при обработке сообщения")

async def main():
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        raise
