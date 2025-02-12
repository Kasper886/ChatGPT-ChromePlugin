import asyncio
import logging
import openai
import os
import re
import glob
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ContentType
from dotenv import load_dotenv
from pydub import AudioSegment

# === Настройка логирования ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")]
)
logger = logging.getLogger(__name__)

# === Загрузка конфигурации ===
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в .env файле")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()
openai.api_key = OPENAI_API_KEY

# === Глобальные переменные ===
DEFAULT_MODEL = "gpt-3.5-turbo"
user_chat_files = {}

# ==== Очистка старых файлов ====
def cleanup_old_files():
    """Удаляет файлы чатов и аудиофайлы старше 10 дней."""
    now = datetime.now()
    cutoff = now - timedelta(days=10)
    
    for file in glob.glob("*-chat-*.txt") + glob.glob("*.ogg"):
        file_time = datetime.fromtimestamp(os.path.getmtime(file))
        if file_time < cutoff:
            os.remove(file)
            logger.info(f"Удален старый файл: {file}")

cleanup_old_files()

# ==== Вспомогательные функции ====
async def create_new_chat_file(user: types.User):
    """Создает новый файл чата для пользователя."""
    timestamp = datetime.now().strftime("%d-%m-%y-%H-%M-%S")
    filename = f"{user.username or user.id}-chat-{timestamp}.txt"
    user_chat_files[user.id] = filename
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Chat started\n")
    logger.info(f"Создан файл чата: {filename}")
    return filename

async def get_chat_file(user: types.User):
    """Возвращает текущий файл чата пользователя или None, если он не существует."""
    files = glob.glob(f"{user.username or user.id}-chat-*.txt")
    return files[0] if files else None

async def append_to_chat_file(user: types.User, text: str):
    """Добавляет текст в файл чата пользователя."""
    chat_file = await get_chat_file(user)
    if chat_file:
        with open(chat_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

async def transcribe_audio(audio_path: str) -> str:
    """Распознает голосовое сообщение."""
    try:
        audio = AudioSegment.from_ogg(audio_path)
        mp3_path = audio_path.replace(".ogg", ".mp3")
        audio.export(mp3_path, format="mp3")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        with open(mp3_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return response.text
    except Exception as e:
        logger.error(f"Ошибка при обработке аудио: {e}")
        return None

async def chat_with_gpt(user: types.User, text: str) -> str:
    """Отправляет сообщение в ChatGPT и получает ответ."""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": text}]
        )
        bot_response = response.choices[0].message.content
        await append_to_chat_file(user, f"Bot: {bot_response}")
        return bot_response
    except Exception as e:
        logger.error(f"Ошибка в chat_with_gpt: {e}")
        return "Ошибка обработки сообщения."

# ==== Обработчики команд ====
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для общения с ChatGPT.\n\n"
        "🤖 Доступные команды:\n"
        "/startnewchat - Начать новый чат\n"
        "/setmodel - Выбрать модель\n"
        "/currentmodel - Текущая модель"
    )

@router.message(Command("startnewchat"))
async def start_new_chat(message: Message):
    filename = await create_new_chat_file(message.from_user)
    await message.answer(f"🆕 Новый чат начат. Файл: {filename}")

# ==== Обработка сообщений ====
@router.message()
async def handle_text_messages(message: Message):
    if message.text and not await get_chat_file(message.from_user):
        await message.answer("❌ У вас нет активного чата. Введите /startnewchat, чтобы начать новый.")
        return
async def handle_messages(message: Message):
    if message.content_type == ContentType.VOICE:
        voice_file = await bot.get_file(message.voice.file_id)
        voice_path = f"{voice_file.file_id}.ogg"
        await bot.download_file(voice_file.file_path, voice_path)
        text = await transcribe_audio(voice_path)
        if text:
            response = await chat_with_gpt(message.from_user, text)
            await message.reply(response)
        return

    user_message = message.text.strip()
    if user_message:
        response = await chat_with_gpt(message.from_user, user_message)
        await message.reply(response)

# === Запуск бота ===
dp.include_router(router)

async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")