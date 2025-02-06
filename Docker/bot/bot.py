import asyncio
import logging
import openai
import os
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
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

# List of available models
AVAILABLE_MODELS = ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
selected_model = "gpt-3.5-turbo"  # Default model

# Function to change model
@dp.message(lambda message: message.text.startswith("/setmodel"))
async def set_model(message: Message):
    global selected_model
    model_name = message.text.split(" ", 1)[-1]

    if model_name in AVAILABLE_MODELS:
        selected_model = model_name
        await message.answer(f"✅ Model changed to: {selected_model}")
    else:
        await message.answer(f"❌ Invalid model name. Available models: {', '.join(AVAILABLE_MODELS)}")

# Function to interact with ChatGPT
async def chat_with_gpt(user_message: str) -> str:
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=selected_model,  # Uses the selected model
            messages=[{"role": "user", "content": user_message}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# Telegram bot handlers
@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer("Hello! I am a bot connected to ChatGPT. Ask me anything!\n"
                         "To change the model, use /setmodel <model_name>")

@dp.message()
async def handle_message(message: Message):
    response = await chat_with_gpt(message.text)
    await message.answer(response)

# Flask webhook for Google Meet
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