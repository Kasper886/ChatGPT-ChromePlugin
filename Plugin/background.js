// background.js

// Load environment variables from env.json
fetch('env.json')
    .then(response => response.json())
    .then(env => {
        const TELEGRAM_BOT_TOKEN = env.TELEGRAM_BOT_TOKEN;
        const TELEGRAM_CHAT_ID = env.TELEGRAM_CHAT_ID;

        chrome.runtime.onInstalled.addListener(() => {
            console.log("Google Meet Audio to ChatGPT extension installed");
        });

        chrome.action.onClicked.addListener((tab) => {
            chrome.tabCapture.capture({
                audio: true,
                video: false
            }, async (stream) => {
                if (stream) {
                    const audioContext = new AudioContext();
                    await audioContext.audioWorklet.addModule('processor.js'); // Load custom audio processor

                    const source = audioContext.createMediaStreamSource(stream);
                    const processorNode = new AudioWorkletNode(audioContext, 'audio-processor');

                    source.connect(processorNode);
                    processorNode.connect(audioContext.destination);

                    processorNode.port.onmessage = (event) => {
                        const audioData = event.data;
                        fetch("http://localhost:5000/transcribe", { // Send audio to server
                            method: "POST",
                            body: JSON.stringify({ audio: Array.from(audioData) }),
                            headers: { "Content-Type": "application/json" }
                        })
                        .then(response => response.json())
                        .then(data => {
                            fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
                                method: "POST",
                                body: JSON.stringify({
                                    chat_id: TELEGRAM_CHAT_ID,
                                    text: data.transcription
                                }),
                                headers: { "Content-Type": "application/json" }
                            });
                        });
                    };
                }
            });
        });
    })
    .catch(error => console.error("Error loading environment variables:", error));