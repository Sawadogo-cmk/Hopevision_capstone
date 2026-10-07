import subprocess
import threading
from detection_config import PIPER, VOICE_MODEL

# =========================
# NORMALISATION TEXTE
# =========================
def normalize_text(text):

    text = text.lower().strip()

    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "ù": "u",
        "ô": "o",
        "î": "i"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text

# =========================
# SPEAK
# =========================
def speak_async(text):

    def run():

        try:

            cmd = (
                f'echo "{text}" | '
                f'{PIPER} '
                f'-m {VOICE_MODEL} '
                f'-f temp_detection.wav'
            )

            subprocess.run(cmd, shell=True)
            subprocess.run("aplay -q temp_detection.wav", shell=True)

        except Exception as e:
            print("❌ Erreur voix :", e)

    threading.Thread(target=run, daemon=True).start()