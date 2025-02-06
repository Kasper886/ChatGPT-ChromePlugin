import asyncio
import logging
import openai
import os
import threading
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

openai.api_key = OPENAI_API_KEY

# Function to interact with ChatGPT
async def chat_with_gpt(user_message: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_message}]
    )
    return response["choices"][0]["message"]["content"]

# Telegram bot handlers
@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer("Hello! I am a bot connected to ChatGPT. Ask me anything!")

@dp.message()
async def handle_message(message: Message):
    response = await chat_with_gpt(message.text)
    await message.answer(response)

# Flask route for Google Meet webhook
@app.route("/meet_webhook", methods=["POST"])
def meet_webhook():
    data = request.json
    if "text" in data:
        user_message = data["text"]
        response = asyncio.run(chat_with_gpt(user_message))
        asyncio.run(send_telegram_message(response))
    return jsonify({"status": "ok"})

async def send_telegram_message(text: str):
    await bot.send_message(os.getenv("TELEGRAM_CHAT_ID"), text)

# Function to run Telegram bot in a separate thread
def run_telegram_bot():
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    # Запускаем Telegram-бота в отдельном потоке
    threading.Thread(target=run_telegram_bot, daemon=True).start()

    # Запускаем Flask-сервер
    app.run(host="0.0.0.0", port=5000)