FROM python:3.9

# Set the working directory
WORKDIR /bot

# Copy dependency file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot's source code
COPY . .

# Start the bot
CMD ["python", "bot.py"]