import asyncio
import logging
import openai
import os
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ChatType, ContentType
from dotenv import load_dotenv
from models_list import AVAILABLE_MODELS  # Import available models from an external file

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
router = Router()  # Добавляем Router
openai.api_key = OPENAI_API_KEY

# === Константы и глобальные переменные ===
SALUTESPEECH_BOT_USERNAME = "smartspeech_sber_bot"
SELECTED_MODEL_FILE = "selected_model.txt"
DEFAULT_MODEL = "gpt-3.5-turbo"
current_chat_file = None

# ==== Вспомогательные функции ====
async def create_new_chat_file():
    global current_chat_file
    timestamp = datetime.now().strftime("chat-%d-%m-%y-%H-%M-%S.txt")
    current_chat_file = timestamp
    with open(current_chat_file, "w", encoding="utf-8") as f:
        f.write("Chat started\n")
    logger.info(f"Новый файл чата создан: {current_chat_file}")

async def append_to_chat_file(text):
    if current_chat_file:
        with open(current_chat_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

async def save_selected_model(model_name):
    with open(SELECTED_MODEL_FILE, "w", encoding="utf-8") as f:
        f.write(model_name)
    logger.info(f"✅ Модель сохранена: {model_name}")

async def load_selected_model():
    if os.path.exists(SELECTED_MODEL_FILE):
        with open(SELECTED_MODEL_FILE, "r", encoding="utf-8") as f:
            model = f.read().strip()
            if model:
                return model
    return DEFAULT_MODEL

# === Фильтрация сообщений ===

def clean_transcribed_message(text: str) -> str:
    """Очищает текст от лишних элементов, оставляя только распознанное сообщение."""
    patterns_to_remove = [
        r"Голосовое сообщение от .+?:",  # Убираем имя отправителя
        r"Голосовое сообщение$",  # Просто "Голосовое сообщение"
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, "", text).strip()

    return text if text else None


# === Обработчики команд ===
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
    await create_new_chat_file()
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    await message.answer(f"🆕 Новый чат начат: {timestamp}")

@router.message(Command("currentmodel"))
async def current_model(message: Message):
    selected_model = await load_selected_model()
    await message.answer(f"🛠 Текущая модель: {selected_model}")

@router.message(Command("setmodel"))
async def set_model_command(message: Message):
    buttons = []
    row = []
    for i, model in enumerate(AVAILABLE_MODELS):
        row.append(InlineKeyboardButton(text=model, callback_data=f"setmodel_{model}"))
        if len(row) == 2 or i == len(AVAILABLE_MODELS) - 1:
            buttons.append(row)
            row = []

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Select a model:", reply_markup=keyboard)

@router.callback_query()
async def model_selected(callback_query: CallbackQuery):
    model_name = callback_query.data.replace("setmodel_", "")
    if model_name in AVAILABLE_MODELS:
        await save_selected_model(model_name)
        await callback_query.message.edit_text(f"✅ Модель изменена на: {model_name}")
    else:
        await callback_query.answer("❌ Ошибка выбора модели.", show_alert=True)

async def chat_with_gpt_proxy(message: Message, cleaned_text: str):
    """Обертка для вызова chat_with_gpt с очищенным текстом."""
    fake_message = Message(
        message_id=message.message_id,
        from_user=message.from_user,
        chat=message.chat,
        text=cleaned_text
    )
    await chat_with_gpt(fake_message)

#@router.message() 
async def chat_with_gpt(message: Message):
    try:
        user_message = message.text.strip()
        if not user_message:
            await message.reply("❌ Пустое сообщение.")
            return

        selected_model = await load_selected_model()

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": user_message}]
        )

        bot_response = response.choices[0].message.content
        await append_to_chat_file(f"User: {user_message}\nBot: {bot_response}")
        await message.reply(bot_response)

    except Exception as e:
        logger.error(f"Ошибка в chat_with_gpt: {str(e)}")
        await message.reply("❌ Ошибка обработки сообщения.")


# === Использование этой обработки вместо chat_with_gpt
SALUTESPEECH_BOT_ID = 8036450123

def clean_transcribed_message(text: str) -> str:
    """Очищает текст от ненужных элементов."""
    patterns_to_remove = [
        r"Голосовое сообщение от .+?:",  # Убираем имя отправителя
        r"Голосовое сообщение$",
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, "", text).strip()

    return text if text else None

@router.message()
async def handle_messages(message: Message):
    """Обрабатывает сообщения и копирует их в группу для теста."""
    if message.content_type == ContentType.VOICE:
        return  # Игнорируем аудио
    
    if message.from_user.id == SALUTESPEECH_BOT_ID:
        text = message.text or message.caption  # Telegram может отправлять текст в caption
        
        logger.info(f"[DEBUG] Сообщение от SaluteSpeech Bot: {text}")  # Логируем текст
        
        if text and text.lower() != "получено аудио":
            cleaned_text = clean_transcribed_message(text)
            if cleaned_text:
                logger.info(f"[DEBUG] Очищенный текст: {cleaned_text}")  # Лог очищенного текста
                
                # Копируем сообщение в группу
                await message.bot.send_message(
                    chat_id=message.chat.id,  # Отправляем в тот же чат
                    text=f"🔄 Пересланное сообщение: {cleaned_text}"
                )

                # Передаем в GPT (если надо)
                await chat_with_gpt_proxy(message, cleaned_text)

    else:
        await chat_with_gpt(message)

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