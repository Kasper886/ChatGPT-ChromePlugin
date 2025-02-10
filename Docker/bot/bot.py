import asyncio
import logging
import openai
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.enums import ChatType, ContentType
from dotenv import load_dotenv
from models_list import AVAILABLE_MODELS  # Подключите доступные модели из файла models_list.py

# === Настройка логирования ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
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
openai.api_key = OPENAI_API_KEY

# === Константы и глобальные переменные ===
SELECTED_MODEL_FILE = "selected_model.txt"
DEFAULT_MODEL = "gpt-3.5-turbo"
current_chat_file = None

# ==== Вспомогательные функции ====
async def create_new_chat_file():
    global current_chat_file
    timestamp = datetime.now().strftime("chat-%d-%m-%y-%H-%M-%S.txt")
    current_chat_file = timestamp
    with open(current_chat_file, "w", encoding='utf-8') as f:
        f.write("Chat started\n")
    logger.info(f"Новый файл чата создан: {current_chat_file}")

async def append_to_chat_file(text):
    if current_chat_file:
        with open(current_chat_file, "a", encoding='utf-8') as f:
            f.write(text + "\n")

async def save_selected_model(model_name):
    with open(SELECTED_MODEL_FILE, "w", encoding='utf-8') as f:
        f.write(model_name)
    logger.info(f"✅ Модель сохранена: {model_name}")

async def load_selected_model():
    if os.path.exists(SELECTED_MODEL_FILE):
        with open(SELECTED_MODEL_FILE, "r", encoding='utf-8') as f:
            model = f.read().strip()
            if model in AVAILABLE_MODELS:
                return model
    return DEFAULT_MODEL

def clean_message(text: str) -> str:
    """
    Очищает текст сообщения от служебных фраз (например, «Голосовое сообщение»).
    """
    unwanted_phrases = ["Голосовое сообщение", "Voice message", "Аудиосообщение", "Audio message"]
    for phrase in unwanted_phrases:
        text = text.replace(phrase, "").strip()
    return text if text != "" else None

# === Обработчики команд ===
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Используйте /startnewchat для начала нового чата.")

@dp.message(Command("startnewchat"))
async def start_new_chat(message: Message):
    await create_new_chat_file()
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    await message.answer(f"🆕 Новый чат начат: {timestamp}")

@dp.message(Command("setmodel"))
async def set_model_command(message: Message):
    buttons = []
    row = []
    for i, model in enumerate(AVAILABLE_MODELS):
        row.append(InlineKeyboardButton(text=model, callback_data=f"setmodel_{model}"))
        if len(row) == 2 or i == len(AVAILABLE_MODELS) - 1:
            buttons.append(row)
            row = []
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите модель:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('setmodel_'))
async def model_selected(callback_query: CallbackQuery):
    model_name = callback_query.data.replace("setmodel_", "")
    if model_name in AVAILABLE_MODELS:
        await save_selected_model(model_name)
        await callback_query.message.edit_text(f"✅ Модель изменена на: {model_name}")
        logger.info(f"Модель выбрана: {model_name}")
    else:
        await callback_query.answer("❌ Некорректный выбор модели", show_alert=True)

@dp.message(Command("currentmodel"))
async def current_model(message: Message):
    selected_model = await load_selected_model()
    await message.answer(f"🛠 Текущая модель: {selected_model}")

# === Обработчик текстовых сообщений ===
async def chat_with_gpt(message: Message):
    try:
        if message.chat.type != ChatType.PRIVATE:  # Игнорируем сообщения из групп
            if message.is_automatic_forward or message.forward_from:
                return
        
        user_message = clean_message(message.text)
        if not user_message:
            if message.chat.type == ChatType.PRIVATE:
                await message.answer("❌ Отправьте текстовое сообщение.")
            return

        # Проверяем, существует ли файл чата
        if not current_chat_file or not os.path.exists(current_chat_file):
            await message.answer("❌ Начните новый чат командой /startnewchat")
            return

        selected_model = await load_selected_model()
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        # Читаем историю чатов
        messages = []
        if current_chat_file:
            with open(current_chat_file, "r", encoding='utf-8') as f:
                for line in f:
                    if line.startswith("User:"):
                        content = clean_message(line.replace("User: ", "").strip())
                        if content:
                            messages.append({"role": "user", "content": content})
                    elif line.startswith("Bot:"):
                        messages.append({"role": "assistant", "content": line.replace("Bot: ", "").strip()})
        
        # Добавляем новое сообщение
        messages.append({"role": "user", "content": user_message})
        
        # Отправляем запрос в ChatGPT
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages
        )
        bot_response = response.choices[0].message.content
        await append_to_chat_file(f"User: {user_message}")
        await append_to_chat_file(f"Bot: {bot_response}")
        await message.answer(bot_response)

    except Exception as e:
        logger.error(f"Ошибка в chat_with_gpt: {str(e)}")
        if message.chat.type == ChatType.PRIVATE:
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@dp.message()
async def handle_messages(message: Message):
    if message.content_type == ContentType.TEXT and not message.text.startswith('/'):
        await chat_with_gpt(message)

# === Запуск бота ===
async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
