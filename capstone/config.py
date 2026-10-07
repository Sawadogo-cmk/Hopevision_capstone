import os

# =========================
# CHEMINS
# =========================
PIPER       = os.path.expanduser("~/piper_bin/piper/piper")
VOICE_MODEL = os.path.expanduser("~/HopeVision/fr_FR-siwis-medium.onnx")
YOLO_MODEL  = "best.pt"
VOSK_MODEL  = "vosk-model-small-fr-0.22"
TEMP_WAV    = "temp.wav"

# =========================
# CAMERA
# =========================
CAMERA_INDEX  = 0
FRAME_WIDTH   = 640
FRAME_HEIGHT  = 480

# =========================
# YOLO
# =========================
YOLO_IMGSZ  = 256
YOLO_CONF   = 0.65
YOLO_DEVICE = "cpu"

# =========================
# DETECTION
# =========================
COOLDOWN = 4   # secondes entre deux annonces vocales

# =========================
# MICRO
# =========================
AUDIO_DEVICE    = 1
AUDIO_BLOCKSIZE = 8000
AUDIO_READ_SIZE = 4000

# =========================
# GSM
# =========================
GSM_PORT = "/dev/ttyUSB2"
GSM_BAUD = 115200

# =========================
# FLASK
# =========================
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

# =========================
# CONTACTS SMS
# =========================
CONTACTS = {
    "djibril"    : "94301404",
    "aziz"       : "94855991",
    "noe"        : "22770012389",
    "halimah"    : "22787221043",
    "call center": "121",
}

# =========================
# MOTS CLES VOCAUX
# =========================
ACTIVATE_KEYWORDS = [
    "active", "activer", "activation",
    "demarre", "lance", "commence",
    "start", "ouvre", "allume",
]

STOP_KEYWORDS = [
    "arrete", "arreter", "stop",
    "desactive", "coupe", "ferme", "eteins",
]

# =========================
# LABELS OBJETS DETECTES
# =========================
OBJECT_LABELS = {
    "personnes"          : ("Une personne detectee",  "{n} personnes detectees"),
    "voitures"           : ("Une voiture detectee",   "{n} voitures detectees"),
    "moto"               : ("Une moto detectee",      "{n} motos detectees"),
    "chaises"            : ("Une chaise detectee",    "{n} chaises detectees"),
    "bouteille_plastique": ("Une bouteille detectee", "{n} bouteilles detectees"),
}