# voice_utils.py
import subprocess
import threading
import json
from vosk import Model, KaldiRecognizer
import sounddevice as sd
from config import VOSK_MODEL_PATH, PIPER, VOICE_MODEL, normalize_text

# =========================
# VOSK MODEL (singleton)
# =========================
_vosk_model = None

def get_vosk_model():
    global _vosk_model
    if _vosk_model is None:
        print("🔄 Chargement Vosk...")
        _vosk_model = Model(VOSK_MODEL_PATH)
        print("✅ Vosk prêt")
    return _vosk_model

# =========================
# VOIX
# =========================
def speak_async(text):
    def run():
        try:
            print("🗣️ Assistant :", text)
            cmd = f'echo "{text}" | {PIPER} -m {VOICE_MODEL} -f temp.wav'
            subprocess.run(cmd, shell=True)
            subprocess.run("aplay -q temp.wav", shell=True)
        except Exception as e:
            print("❌ Erreur voix :", e)
    
    threading.Thread(target=run, daemon=True).start()

# =========================
# ECOUTE VOCALE GENERIQUE
# =========================
def create_voice_listener(callback, device_id=1):
    """Crée un thread d'écoute vocale qui appelle callback(text)"""
    
    def voice_control():
        vosk_model = get_vosk_model()
        
        print(sd.query_devices())
        device_info = sd.query_devices(device_id, 'input')
        samplerate = int(device_info['default_samplerate'])
        
        print("🎤 Micro :", device_info['name'])
        print("🎤 Sample rate :", samplerate)
        
        recognizer = KaldiRecognizer(vosk_model, samplerate)
        print("🎤 Écoute vocale active...")
        
        with sd.RawInputStream(
            samplerate=samplerate,
            blocksize=8000,
            device=device_id,
            dtype='int16',
            channels=1
        ) as stream:
            while True:
                data, overflowed = stream.read(4000)
                audio_data = bytes(data)
                
                if recognizer.AcceptWaveform(audio_data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "")
                    text = normalize_text(text)
                    
                    if text:
                        print("🗣️ Reconnu :", text)
                        callback(text)
    
    thread = threading.Thread(target=voice_control, daemon=True)
    thread.start()
    return thread