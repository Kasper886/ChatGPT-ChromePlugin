// content.js
console.log("Google Meet Audio to ChatGPT content script loaded");

// Добавляем индикатор записи в интерфейс Google Meet
const indicator = document.createElement("div");
indicator.id = "recording-indicator";
indicator.style.position = "fixed";
indicator.style.top = "10px";
indicator.style.right = "10px";
indicator.style.backgroundColor = "red";
indicator.style.color = "white";
indicator.style.padding = "5px 10px";
indicator.style.borderRadius = "5px";
indicator.style.display = "none";
indicator.innerText = "Recording...";
document.body.appendChild(indicator);

// Слушаем сообщения от background.js
chrome.runtime.onMessage.addListener((message) => {
    if (message.action === "start_capture") {
        indicator.style.display = "block";
    } else if (message.action === "stop_capture") {
        indicator.style.display = "none";
    }
});