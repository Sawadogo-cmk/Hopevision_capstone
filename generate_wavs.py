import os
import subprocess

# =========================
# CONFIG PIPER
# =========================
PIPER_PATH = os.path.expanduser("~/piper_bin/piper/piper")
VOICE_MODEL = os.path.expanduser("~/HopeVision/fr_FR-siwis-medium.onnx")
OUTPUT_DIR = "sounds"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# LABELS AUDIO HOPEVISION
# =========================
LABELS_AUDIO = {
    "bonjour": "Bonjour, système HopeVision activé.",
    "personnes": "Une personne est devant vous.",
    "voitures": "Une voiture est détectée.",
    "moto": "Une moto est détectée.",
    "chaises": "Une chaise est détectée.",
    "bouteille_plastique": "Une bouteille en plastique est détectée."
}

# =========================
# GENERATION WAV
# =========================
def generate_wav(text, output_file):
    cmd = [
        PIPER_PATH,
        "-m", VOICE_MODEL,
        "-f", output_file
    ]

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    process.communicate(text.encode("utf-8"))

# =========================
# MAIN
# =========================
print("🎧 Génération des fichiers audio...")

for label, text in LABELS_AUDIO.items():
    wav_path = os.path.join(OUTPUT_DIR, f"{label}.wav")

    if os.path.exists(wav_path):
        print(f"✔️ Déjà existant : {label}")
        continue

    print(f"🔊 Génération : {label}")
    generate_wav(text, wav_path)

print("✅ Tous les fichiers WAV sont prêts !")
