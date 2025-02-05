from flask import Flask, request, jsonify
import numpy as np
import torch
import whisper
import requests
import os

app = Flask(__name__)
model = whisper.load_model("base")  # Load Whisper model for transcription

# Retrieve Telegram credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    try:
        data = request.json
        audio_array = np.array(data["audio"], dtype=np.float32)
        
        # Convert audio array to tensor for Whisper processing
        audio_tensor = torch.from_numpy(audio_array)
        result = model.transcribe(audio_tensor)
        transcription = result["text"]
        
        # Send the transcription to Telegram
        send_message_to_telegram(transcription)
        
        return jsonify({"transcription": transcription})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def send_message_to_telegram(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, json=payload)
    else:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)