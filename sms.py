import os
import json
import threading
import subprocess
import time
import queue
import serial
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# =========================
# GSM MODEM
# =========================
PORT = "/dev/ttyUSB2"
BAUD = 115200

# =========================
# CONTACTS
# =========================
contacts = {
    "call center": "121",
    "voice mail": "133",
    "djibril": "94301404",
    "aziz": "94855991",
    "noe": "+22770012389",
    "halimah": "+22787221043"
}

# =========================
# VOSK MODEL
# =========================
print("🔄 Chargement Vosk...")

vosk_model = Model("vosk-model-small-fr-0.22")

print("✅ Vosk prêt")

# =========================
# PIPER TTS
# =========================
PIPER = os.path.expanduser("~/piper_bin/piper/piper")
VOICE_MODEL = os.path.expanduser("~/HopeVision/fr_FR-siwis-medium.onnx")

# =========================
# QUEUE AUDIO PARTAGEE
# =========================
audio_queue = queue.Queue()

# =========================
# GRAMMAIRES VOSK
# Restreint la reconnaissance à des mots précis
# pour éviter les erreurs de transcription
# =========================

# Grammaire pour les noms de contacts
# On ajoute aussi les variantes phonétiques connues
GRAMMAR_CONTACTS = json.dumps([
    "djibril", "aziz", "noe", "noel", "halimah",
    "call center", "voice mail",
    "[unk]"
])

# Grammaire pour la confirmation oui/non
GRAMMAR_CONFIRM = json.dumps([
    "oui", "non", "yes", "no",
    "envoie", "annule", "annuler",
    "[unk]"
])

# =========================
# NORMALISATION TEXTE
# =========================
def normalize_text(text):

    text = text.lower().strip()

    replacements = {
        "é": "e", "è": "e", "ê": "e",
        "à": "a", "â": "a",
        "ù": "u", "û": "u",
        "ô": "o", "î": "i", "ï": "i",
        "ç": "c",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text

# =========================
# SPEAK (SYNCHRONE)
# Vide la queue avant/après pour éviter l'auto-écoute
# =========================
def speak(text):

    print(f"🔊 Parole : {text}")

    _flush_queue()

    try:

        cmd = (
            f'echo "{text}" | '
            f'{PIPER} '
            f'-m {VOICE_MODEL} '
            f'-f temp_sms.wav'
        )

        subprocess.run(cmd, shell=True)
        subprocess.run("aplay -q temp_sms.wav", shell=True)

    except Exception as e:

        print("❌ Erreur voix :", e)

    time.sleep(0.4)
    _flush_queue()

def _flush_queue():
    """Vide la queue audio pour éviter les restes de son."""
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break

# =========================
# LISTEN ONCE
# Lit depuis la queue partagée
# grammar=None → reconnaissance libre (pour le message)
# grammar=str  → reconnaissance restreinte (contacts, oui/non)
# =========================
def listen_once(samplerate, timeout=10, grammar=None):
    """
    Retourne le premier texte reconnu ou "" si timeout.
    """

    if grammar:
        recognizer = KaldiRecognizer(vosk_model, samplerate, grammar)
    else:
        recognizer = KaldiRecognizer(vosk_model, samplerate)

    start = time.time()

    print("🎧 Écoute en cours...")

    while True:

        if time.time() - start > timeout:
            print("⏱️ Timeout écoute")
            return ""

        try:
            audio_data = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if recognizer.AcceptWaveform(audio_data):

            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            text = normalize_text(text)

            if text and text != "[unk]":
                print(f"🗣️ Reconnu : {text}")
                return text

# =========================
# TROUVER CONTACT
# Variantes phonétiques incluses
# =========================

# Alias phonétiques pour les noms difficiles
contact_aliases = {
    "noe":      ["noe", "noel", "noel", "no", "noe"],
    "aziz":     ["aziz", "asis"],
    "halimah":  ["halimah", "halima", "alima"],
    "voice mail": ["voice mail", "voicemail", "boite vocale"],
}

def find_contact(text):
    """
    Cherche dans le texte un nom de contact (avec aliases).
    Retourne (nom_affiche, numero) ou (None, None).
    """
    normalized = normalize_text(text)

    for name, number in contacts.items():

        # Vérifie le nom principal
        if normalize_text(name) in normalized:
            return name, number
        # Vérifie les aliases
        aliases = contact_aliases.get(name, [])

        for alias in aliases:

            if normalize_text(alias) in normalized:
                return name, number

    return None, None

# =========================
# ENVOYER SMS VIA MODEM GSM
# =========================
def send_sms(numero, message):

    print(f"📤 Envoi SMS à {numero} : {message}")

    try:

        ser = serial.Serial(PORT, BAUD, timeout=5)
        time.sleep(1)
        ser.write(b'AT+CMGF=1\r')
        time.sleep(0.5)
        cmd_dest = f'AT+CMGS="{numero}"\r'
        ser.write(cmd_dest.encode())
        time.sleep(0.5)
        ser.write((message + chr(26)).encode('utf-8'))
        time.sleep(3)

        response = ser.read(ser.in_waiting).decode(errors='ignore')
        ser.close()

        print("📬 Réponse modem :", response)

        if "+CMGS" in response:
            return True
        else:
            print("⚠️ Réponse inattendue :", response)
            return False

    except Exception as e:

        print("❌ Erreur modem :", e)
        return False

# =========================
# FLUX SMS VOCAL COMPLET
# =========================
def sms_flow(samplerate):

    # --- ETAPE 1 : A QUI ? ---
    speak("A qui voulez-vous envoyer le message ?")

    contact_name = None
    contact_number = None

    for _ in range(3):

        # Grammaire restreinte aux noms de contacts
        text = listen_once(
            samplerate=samplerate,
            timeout=8,
            grammar=GRAMMAR_CONTACTS
        )
        if not text:
            speak("Je n'ai pas entendu. Répétez le nom.")
            continue
        contact_name, contact_number = find_contact(text)

        if contact_name:
            speak(f"Très bien. Message pour {contact_name}.")
            break
        else:
            speak(
                "Je n'ai pas reconnu ce nom. "
                "Dites par exemple : Noe, Aziz,  Halimah."
            )

    if not contact_name:
        speak("Impossible de trouver le contact. Annulation.")
        return

    # --- ETAPE 2 : QUEL MESSAGE ? ---
    speak("Quel est votre message ? Parlez maintenant.")

    message_text = ""

    for _ in range(3):

        # Reconnaissance libre pour le message
        text = listen_once(
            samplerate=samplerate,
            timeout=15,
            grammar=None
        )

        if text:
            message_text = text
            break
        else:
            speak("Je n'ai pas entendu le message. Veuillez répéter.")

    if not message_text:
        speak("Aucun message capturé. Annulation.")
        return

    # --- ETAPE 3 : CONFIRMATION ---
    speak(
        f"Voulez-vous envoyer le message : "
        f"{message_text} "
        f"a {contact_name} ? "
        f"Dites oui ou non."
    )

    confirmed = False
    got_answer = False

    for _ in range(3):

        # Grammaire restreinte oui/non
        text = listen_once(
            samplerate=samplerate,
            timeout=8,
            grammar=GRAMMAR_CONFIRM
        )

        if not text:
            speak("Je n'ai pas compris. Dites oui ou non.")
            continue

        if "oui" in text or "yes" in text or "envoie" in text:
            confirmed = True
            got_answer = True
            break

        elif "non" in text or "no" in text or "annule" in text:
            confirmed = False
            got_answer = True
            break

        else:
            speak("Dites oui pour envoyer, ou non pour annuler.")

    if not got_answer:
        speak("Pas de réponse. Annulation par sécurité.")
        return

    # --- ETAPE 4 : ENVOI ---
    if confirmed:

        speak("Envoi du message en cours.")

        success = send_sms(contact_number, message_text)

        if success:
            speak(f"Message envoyé avec succès a {contact_name}.")
        else:
            speak("Echec de l'envoi. Vérifiez le modem.")

    else:

        speak("Message annulé.")

# =========================
# MOTS CLES DECLENCHEURS
# =========================
sms_keywords = [
    "envoie un message",
    "envoyer un message",
    "envoie message",
    "envoyer message",
    "envoie un sms",
    "envoyer un sms",
]

# =========================
# BOUCLE PRINCIPALE
# Un seul stream -> audio_queue
# =========================
def voice_loop(device_id=1):

    device_info = sd.query_devices(device_id, 'input')
    samplerate = int(device_info['default_samplerate'])

    print(f"🎤 Micro : {device_info['name']}")
    print(f"🎤 Sample rate : {samplerate}")

    kw_recognizer = KaldiRecognizer(vosk_model, samplerate)

    sms_in_progress = False

    print("🎤 Écoute vocale SMS active...")
    print("💬 Dites 'envoie un message' pour commencer.")

    def audio_callback(indata, frames, time_info, status):
        audio_queue.put(bytes(indata))

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        device=device_id,
        dtype='int16',
        channels=1,
        callback=audio_callback
    ):

        print("✅ Stream audio ouvert.")

        while True:

            if sms_in_progress:
                time.sleep(0.05)
                continue

            try:
                audio_data = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if kw_recognizer.AcceptWaveform(audio_data):

                result = json.loads(kw_recognizer.Result())
                text = result.get("text", "")
                text = normalize_text(text)

                if not text:
                    continue

                print(f"🗣️ Reconnu : {text}")

                if any(kw in text for kw in sms_keywords):

                    sms_in_progress = True

                    print("📨 Déclenchement flux SMS")

                    kw_recognizer = KaldiRecognizer(
                        vosk_model, samplerate
                    )

                    sms_flow(samplerate=samplerate)

                    sms_in_progress = False

                    kw_recognizer = KaldiRecognizer(
                        vosk_model, samplerate
                    )

                    print("✅ Flux SMS terminé. Retour à l'écoute.")

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    print("🚀 SMS.py démarré")

    print(sd.query_devices())

    device_id = 1

    speak(
        "Système SMS prêt. "
        "Dites envoie un message pour commencer."
    )

    voice_loop(device_id=device_id)