import json
import queue
import sys
import time
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from config import settings
import os

# Load Vosk model path and sample rate from settings or defaults
MODEL_PATH = getattr(settings, "VOSK_MODEL_PATH", "models/vosk-model-small-ja-0.22")
SAMPLE_RATE = int(getattr(settings, "VOSK_SAMPLE_RATE", 16000))

# Lazy-load Vosk model to avoid import-time errors
_model = None

def _load_model():
    global _model
    if _model is None:
        if not MODEL_PATH or not os.path.isdir(MODEL_PATH):
            raise RuntimeError(f"Vosk model path '{MODEL_PATH}' not found. Please download and unpack the model under this path.")
        _model = Model(MODEL_PATH)
    return _model

def listen(duration: int = 5) -> str:
    """
    Listen to microphone for up to 'duration' seconds and return recognized text.
    """
    rec = KaldiRecognizer(_load_model(), SAMPLE_RATE)
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16', channels=1, callback=callback):
        result_text = ""
        start_time = time.time()
        while True:
            if not q.empty():
                data = q.get()
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    result_text = res.get("text", "")
                    break
            if time.time() - start_time > duration:
                break
        if not result_text:
            res = json.loads(rec.FinalResult())
            result_text = res.get("text", "")
    return result_text
