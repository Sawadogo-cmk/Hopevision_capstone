import queue
import sounddevice as sd
import json
from vosk import Model, KaldiRecognizer

MODEL_PATH = "vosk-model-small-fr-0.22"

q = queue.Queue()

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, 16000)


def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))


def listen_command():
    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=callback
    ):
        print("🎤 VOSK actif...")

        while True:
            data = q.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()

                if text:
                    print("🗣️ Commande :", text)
                    return text.lower()