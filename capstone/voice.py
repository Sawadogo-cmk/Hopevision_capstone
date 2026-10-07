import json
import time
import unicodedata

import sounddevice as sd
from vosk import Model, KaldiRecognizer

import config
from speaker import speak, speak_async


# =========================
# UTILITAIRES
# =========================

def normalize(text: str) -> str:
    """Minuscules + suppression des accents (pour le matching vocal)."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def is_yes(text: str) -> bool:
    t = normalize(text)
    return any(w in t for w in ["oui", "ok", "yes", "d accord"])


# =========================
# ECOUTE UNIQUE
# =========================

def listen_once(rec, stream, timeout: float = 6) -> str:
    """
    Lit le flux audio et retourne le premier énoncé reconnu,
    ou une chaîne vide si le timeout est atteint.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            data, _ = stream.read(config.AUDIO_READ_SIZE)
            if rec.AcceptWaveform(bytes(data)):
                result = json.loads(rec.Result())
                text   = normalize(result.get("text", ""))
                if text:
                    print("🧠 HEARD :", text)
                    return text
        except Exception:
            pass
    return ""


# =========================
# DIALOGUE SMS
# =========================

def _sms_flow(gsm, vosk_model, samplerate, stream) -> None:
    """Dialogue vocal complet pour envoyer un SMS."""

    if not gsm or not gsm.connected:
        speak("Le module SMS n'est pas disponible")
        return

    # 1. Contact
    speak("À qui envoyer le message ?")
    name, number = None, None
    for _ in range(3):
        rec = KaldiRecognizer(vosk_model, samplerate)
        t   = listen_once(rec, stream, timeout=6)
        name, number = gsm.find_contact(t)
        if name:
            break

    if not name:
        speak("Contact introuvable")
        return

    speak(f"Contact {name} trouvé")

    # 2. Message
    speak("Quel est le message ?")
    rec = KaldiRecognizer(vosk_model, samplerate)
    msg = listen_once(rec, stream, timeout=10)
    if not msg:
        speak("Message vide, annulé")
        return

    # 3. Confirmation
    speak(f"Vous avez dit : {msg}")
    speak("Envoyer ? Oui ou non.")
    rec     = KaldiRecognizer(vosk_model, samplerate)
    confirm = listen_once(rec, stream, timeout=6)

    if is_yes(confirm):
        speak("Envoi en cours")
        ok = gsm.send_sms(number, msg)
        speak("Message envoyé" if ok else "Échec de l'envoi")
    else:
        speak("Annulé")


# =========================
# BOUCLE PRINCIPALE
# =========================

def unified_voice_loop(vision, gsm=None) -> None:
    """
    Boucle vocale unique — tourne dans le thread principal.
    Gère sur UN SEUL micro :
      • activer / arrêter la détection YOLO
      • envoyer un SMS par commande vocale (si gsm connecté)
    """
    print("🔄 Chargement Vosk...")
    vosk_model = Model(config.VOSK_MODEL)
    print("✅ Vosk prêt")

    device_info = sd.query_devices(config.AUDIO_DEVICE, "input")
    samplerate  = int(device_info["default_samplerate"])
    print(f"🎤 Micro : {device_info['name']} | {samplerate} Hz")
    print("🎤 Écoute vocale active...")

    with sd.RawInputStream(
        samplerate = samplerate,
        blocksize  = config.AUDIO_BLOCKSIZE,
        device     = config.AUDIO_DEVICE,
        dtype      = "int16",
        channels   = 1,
    ) as stream:

        while True:
            rec  = KaldiRecognizer(vosk_model, samplerate)
            text = listen_once(rec, stream, timeout=8)

            if not text:
                continue

            print("🗣️  Reconnu :", text)

            # ── Activer détection ──────────────────────────
            if any(kw in text for kw in config.ACTIVATE_KEYWORDS):
                if not vision.detection_active:
                    vision.detection_active = True
                    print("✅ Détection activée")
                    speak_async("Détection activée")
                continue

            # ── Arrêter détection ──────────────────────────
            if any(kw in text for kw in config.STOP_KEYWORDS):
                if vision.detection_active:
                    vision.detection_active = False
                    print("🛑 Détection arrêtée")
                    speak_async("Détection arrêtée")
                continue

            # ── Envoyer SMS ────────────────────────────────
            if gsm and any(kw in text for kw in ["sms", "message", "envoie", "envoyer"]):
                _sms_flow(gsm, vosk_model, samplerate, stream)
                continue