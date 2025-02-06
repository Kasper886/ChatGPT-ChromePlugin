// processor.js

class AudioProcessor extends AudioWorkletProcessor {
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input.length > 0) {
            this.port.postMessage(input[0]); // Send audio data back to background.js
        }
        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);