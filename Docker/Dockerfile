# Use official Python image
FROM python:3.9

# Set working directory
WORKDIR /app

# Copy project files
COPY server.py requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start the server
CMD ["python", "server.py"]
