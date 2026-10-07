import os

# =========================
# PIPER (synthèse vocale)
# =========================
PIPER = os.path.expanduser(
    os.getenv("PIPER_PATH", "~/piper_bin/piper/piper")
)

VOICE_MODEL = os.path.expanduser(
    os.getenv("PIPER_VOICE", "~/HopeVision/fr_FR-siwis-medium.onnx")
)

# =========================
# GSM MODEM
# =========================
PORT = os.getenv("GSM_PORT", "/dev/ttyUSB2")
BAUD = int(os.getenv("GSM_BAUD", 115200))

# =========================
# CONTACTS
# ⚠️ Numéros fictifs — remplacer par les vôtres en local
# =========================
contacts = {
    "call center": "121",
    "voice mail":  "133",
    "contact 1":   "+00000000000",
    "contact 2":   "+00000000000",
    "contact 3":   "+00000000000",
}

# =========================
# MOTS CLÉS SMS
# =========================
sms_keywords = [
    "envoie",
    "envoyer",
    "message",
    "sms",
    "texto"
]