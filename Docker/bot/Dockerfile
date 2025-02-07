FROM python:3.9-slim

# Set the working directory
WORKDIR /bot

# Copy dependency file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot's source code
COPY . .

# Copy selected model file
RUN touch /bot/selected_model.txt && chmod 666 /bot/selected_model.txt

# Открываем порт (если бот использует Flask)
EXPOSE 5000

# Start the bot
CMD ["python", "bot.py"]