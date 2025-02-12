import asyncio
import logging
import openai
import os
import re
import subprocess
from pydub import AudioSegment
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
#SELECTED_MODEL_FILE = "selected_model.txt"
DEFAULT_MODEL = "gpt-3.5-turbo"
#current_chat_file = None

# ==== Вспомогательные функции ====
async def get_selected_model_file(username: str) -> str:
    """Формирует уникальное имя файла для выбранной модели"""
    return f"{username}-selected_model.txt"

async def create_new_chat_file(username: str) -> str:
    """Создает новый файл чата для пользователя и возвращает его имя."""
    selected_model_file = await get_selected_model_file(username)

    # Генерируем уникальное имя файла чата
    timestamp = datetime.now().strftime("%d-%m-%y-%H-%M-%S")
    chat_file = f"{username}-chat-{timestamp}.txt"

    # Если файла модели нет — создаем его
    if not os.path.exists(selected_model_file):
        with open(selected_model_file, "w", encoding="utf-8") as f:
            f.write("gpt-3.5-turbo\n")  # По умолчанию используем gpt-3.5-turbo

    # Создаем новый файл чата
    with open(chat_file, "w", encoding="utf-8") as f:
        f.write("Chat started\n")

    logger.info(f"✅ Новый файл чата создан: {chat_file}")
    return chat_file

async def append_to_chat_file(username: str, text: str):
    """Добавляет текст в файл чата пользователя."""
    # Ищем последний (активный) файл чата пользователя
    chat_files = sorted([f for f in os.listdir() if f.startswith(f"{username}-chat")], reverse=True)

    if not chat_files:
        return  # Если чатов нет, не записываем

    chat_file = chat_files[0]  # Берем последний созданный чат

    with open(chat_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")


async def save_selected_model(username: str, model_name: str = DEFAULT_MODEL):
    """Сохраняет выбранную модель в файл пользователя, если модель не указана - записывает модель по умолчанию."""
    selected_model_file = await get_selected_model_file(username)
    
    with open(selected_model_file, "w", encoding="utf-8") as f:
        f.write(model_name)  # Теперь записываем реальную модель, а не просто текст
    logger.info(f"✅ Модель '{model_name}' сохранена в файл: {selected_model_file}")

async def load_selected_model(username: str):
    """Загружает выбранную модель, если файла нет — создает его с моделью по умолчанию."""
    selected_model_file = await get_selected_model_file(username)

    if not os.path.exists(selected_model_file):
        await save_selected_model(username, DEFAULT_MODEL)  # Если файла нет, создаем его с моделью по умолчанию
        return DEFAULT_MODEL

    with open(selected_model_file, "r", encoding="utf-8") as f:
        model = f.read().strip()

    # Проверяем, поддерживается ли загруженная модель, иначе возвращаем модель по умолчанию
    
    if model not in AVAILABLE_MODELS:
        return DEFAULT_MODEL

    return model

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
    username = message.from_user.username or f"user_{message.from_user.id}"
    chat_file = await create_new_chat_file(username)  # Создаём новый чат-файл

    await message.answer(f"✅ Новый чат создан!\nФайл: `{chat_file}`")


@router.message(Command("currentmodel"))
async def current_model(message: Message):
    username = message.from_user.username or f"user_{message.from_user.id}"  # Получаем уникальное имя пользователя
    selected_model = await load_selected_model(username)  # Загружаем модель пользователя
    
    if not selected_model:  # Если файл отсутствует или пустой, возвращаем модель по умолчанию
        selected_model = "gpt-3.5-turbo"

    await message.answer(f"🛠 Текущая модель: `{selected_model}`")


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
    username = message.from_user.username or f"user_{message.from_user.id}"  # Если username нет, используем user_ID
    selected_model_file = await get_selected_model_file(username)
    await message.answer(f"Select a model:\n(Saving to: `{selected_model_file}`)", reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith("setmodel_"))
async def model_selected(callback_query: CallbackQuery):
    model_name = callback_query.data.split("_")[1]  # Извлекаем название модели
    username = callback_query.from_user.username or f"user_{callback_query.from_user.id}"  # Гарантируем уникальное имя

    await save_selected_model(username, model_name)  # Исправленный вызов

    await callback_query.answer(f"✅ Модель '{model_name}' выбрана!")
    await callback_query.message.edit_text(f"🔹 Ваша текущая модель: `{model_name}`")

async def transcribe_audio(audio_path: str) -> str:
    """Преобразует аудио в текст с помощью OpenAI Whisper API (новый синтаксис)."""
    try:
        # Конвертируем OGG в MP3
        audio = AudioSegment.from_ogg(audio_path)
        mp3_path = audio_path.replace(".ogg", ".mp3")
        audio.export(mp3_path, format="mp3")

        # Подключаемся к OpenAI API (новый способ)
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        # Отправляем аудио на распознавание
        with open(mp3_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        return response.text

    except Exception as e:
        logger.error(f"Ошибка распознавания аудио: {e}")
        return None

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

async def chat_with_gpt_file(message: Message):
    """Отправляет файл чата пользователя в GPT и получает ответ."""
    try:
        # Определяем пользователя
        username = message.from_user.username or f"user_{message.from_user.id}"

        # Получаем все файлы чатов пользователя
        chat_files = sorted([f for f in os.listdir() if f.startswith(f"{username}-chat")], reverse=True)

        # Если у пользователя нет файлов чатов — он не может отправить сообщение
        if not chat_files:
            return "❌ У вас нет активного чата. Запустите новый чат командой /startnewchat."

        # Берем самый новый файл чата
        chat_file = chat_files[0]

        # Читаем содержимое файла чата
        with open(chat_file, "r", encoding="utf-8") as f:
            chat_history = f.read()

        # Загружаем выбранную модель или используем модель по умолчанию
        selected_model = await load_selected_model(username)

        # Проверяем, является ли загруженная модель допустимой
        if selected_model not in AVAILABLE_MODELS:
            selected_model = "gpt-3.5-turbo"  # Если файл пуст или модель некорректна, ставим по умолчанию

        # Отправляем в GPT
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "system", "content": "Ты — умный помощник."},
                      {"role": "user", "content": chat_history},
                      {"role": "user", "content": message.text}]  # Добавляем новое сообщение в диалог
        )

        bot_response = response.choices[0].message.content.strip()

        # Записываем сообщение пользователя и ответ бота в файл чата
        with open(chat_file, "a", encoding="utf-8") as f:
            f.write(f"\nUser: {message.text}\nBot: {bot_response}")

        return f"🤖 **[Модель: {selected_model}]**\n\n{bot_response}"

    except Exception as e:
        return f"❌ Ошибка при обращении к GPT: {e}"

@router.message()
async def handle_messages(message: Message):
    """Обрабатывает текстовые и голосовые сообщения, записывает в чат-файл и отправляет в GPT."""
    username = message.from_user.username or f"user_{message.from_user.id}"

    # Ищем файлы чатов пользователя
    chat_files = sorted([f for f in os.listdir() if f.startswith(f"{username}-chat")], reverse=True)

    # Если у пользователя нет активного чата, он не может отправить сообщение
    if message.content_type == ContentType.TEXT and not chat_files:
        await message.answer("❌ У вас нет активного чата. Запустите новый чат командой /startnewchat.")
        return

    # Определяем последний (активный) файл чата пользователя
    chat_file = chat_files[0] if chat_files else None

    # 🎤 Если пришло голосовое сообщение
    if message.content_type == ContentType.VOICE:
        logger.info("🎤 Получено голосовое сообщение, обрабатываем...")

        try:
            # Скачиваем голосовое сообщение
            voice_file = await bot.get_file(message.voice.file_id)
            voice_path = f"{voice_file.file_id}.ogg"
            await bot.download_file(voice_file.file_path, voice_path)

            # Распознаём текст
            text = await transcribe_audio(voice_path)

            if text:
                logger.info(f"✅ Расшифрованный текст: {text}")

                # Убираем "Расшифрованное сообщение:"
                cleaned_text = text.replace("Расшифрованное сообщение:", "").strip()

                # 📢 Отправляем в чат расшифрованное сообщение
                await message.reply(f"🎙 Расшифрованный текст:\n{cleaned_text}")

                # Записываем в файл чата пользователя
                await append_to_chat_file(username, f"User: {cleaned_text}")

                # 🔍 Загружаем выбранную модель
                selected_model = await load_selected_model(username)

                # Проверяем корректность модели
                if selected_model not in AVAILABLE_MODELS:
                    logger.warning(f"⚠️ Некорректная модель '{selected_model}', используем gpt-3.5-turbo")
                    selected_model = "gpt-3.5-turbo"

                # Отправляем в GPT
                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": "Ты — умный помощник."},
                        {"role": "user", "content": cleaned_text}
                    ]
                )

                bot_response = response.choices[0].message.content.strip()

                # Записываем сообщение пользователя и ответ бота в файл чата
                await append_to_chat_file(username, f"Bot: {bot_response}")

                await message.reply(f"🤖 **[Модель: {selected_model}]**\n\n{bot_response}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке голосового сообщения: {e}")
            await message.reply("❌ Ошибка обработки голосового сообщения.")

        return  # Завершаем обработку голосового сообщения

    # 📄 Если пришло текстовое сообщение
    user_message = message.text.strip()
    if user_message:
        await append_to_chat_file(username, f"User: {user_message}")

        if chat_file:
            response = await chat_with_gpt_file(message)  # Диалог
        else:
            response = await chat_with_gpt(message)  # Одиночный ответ

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