import asyncio
import logging
import openai
import os
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

# Function to get available models
async def get_available_models():
    try:
        client = openai.OpenAI()
        models = client.models.list()
        model_list = [model.id for model in models]
        return model_list
    except Exception as e:
        logging.error(f"Error fetching models: {e}")
        return []

# Function to select a model
async def select_model():
    available_models = await get_available_models()
    preferred_models = ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
    for model in preferred_models:
        if model in available_models:
            return model
    return "gpt-3.5-turbo"  # Default fallback model

# Function to interact with ChatGPT
async def chat_with_gpt(user_message: str) -> str:
    try:
        selected_model = await select_model()
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

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
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, run_flask)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())