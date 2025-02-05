// background.js
chrome.runtime.onInstalled.addListener(() => {
    console.log("Google Meet Audio to ChatGPT extension installed");
});

chrome.action.onClicked.addListener((tab) => {
    chrome.tabCapture.capture({
        audio: true,
        video: false
    }, (stream) => {
        if (stream) {
            const audioContext = new AudioContext();
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            source.connect(processor);
            processor.connect(audioContext.destination);

            processor.onaudioprocess = (event) => {
                const audioData = event.inputBuffer.getChannelData(0);
                fetch("https://your-server.com/transcribe", {
                    method: "POST",
                    body: JSON.stringify({ audio: Array.from(audioData) }),
                    headers: { "Content-Type": "application/json" }
                })
                .then(response => response.json())
                .then(data => {
                    fetch("https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage", {
                        method: "POST",
                        body: JSON.stringify({
                            chat_id: "YOUR_CHAT_ID",
                            text: data.transcription
                        }),
                        headers: { "Content-Type": "application/json" }
                    });
                });
            };
        }
    });
});
