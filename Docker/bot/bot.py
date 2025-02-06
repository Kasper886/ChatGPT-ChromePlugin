import logging
import openai
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import CommandStart
#from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read tokens from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Function to interact with ChatGPT
async def chat_with_gpt(user_message: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_message}]
    )
    return response["choices"][0]["message"]["content"]

# Handler for /start command
@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer("Hello! I am a bot connected to ChatGPT. Ask me anything!")

# Handler for messages from Telegram
@dp.message()
async def handle_message(message: Message):
    response = await chat_with_gpt(message.text)
    await message.answer(response)

# Webhook to receive messages from Google Meet
@app.route("/meet_webhook", methods=["POST"])
def meet_webhook():
    data = request.json
    if "text" in data:
        user_message = data["text"]
        response = asyncio.run(chat_with_gpt(user_message))
        asyncio.run(send_telegram_message(response))
    return jsonify({"status": "ok"})

# Function to send messages to Telegram
async def send_telegram_message(text: str):
    await bot.send_message(TELEGRAM_CHAT_ID, text)

# Start bot and Flask server
async def main():
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling(bot))
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    asyncio.run(main())