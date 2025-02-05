FROM python:3.9

# Install dependencies for audio processing (if Whisper requires them)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /server

# Copy dependency file (if available)
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into the container
COPY . .

# Expose Flask port
EXPOSE 5000

# Start the application
CMD ["python", "server.py"]
