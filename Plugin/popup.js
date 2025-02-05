// popup.js
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("startCapture").addEventListener("click", () => {
        chrome.runtime.sendMessage({ action: "start_capture" });
    });
    
    document.getElementById("stopCapture").addEventListener("click", () => {
        chrome.runtime.sendMessage({ action: "stop_capture" });
    });
});