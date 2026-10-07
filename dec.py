from ultralytics import YOLO
import cv2
from flask import Flask, Response
import time
import subprocess
import os
import threading
from collections import Counter

# =========================
# FLASK
# =========================
app = Flask(__name__)

# =========================
# PATHS CORRIGÉS
# =========================
WHISPER = "/home/raspberry/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/home/raspberry/whisper.cpp/models/ggml-small.bin"

AUDIO_FILE = "temp.wav"

# =========================
# YOLO
# =========================
print("🔄 Chargement du modèle YOLO...")
model = YOLO("best.pt")
print("✅ Modèle prêt")
print("📦 Classes :", model.names)

# =========================
# CAMERA
# =========================
cap = cv2.VideoCapture(1, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("❌ Caméra introuvable")
    exit()

# =========================
# ETAT
# =========================
detection_active = False
last_time = 0
cooldown = 4
last_counts = {}

# =========================
# VOIX (PIPER)
# =========================
PIPER = os.path.expanduser("~/piper_bin/piper/piper")
VOICE_MODEL = os.path.expanduser("~/HopeVision/fr_FR-siwis-medium.onnx")

def speak(text):
    try:
        cmd = f'echo "{text}" | {PIPER} -m {VOICE_MODEL} -f temp.wav'
        subprocess.run(cmd, shell=True)
        subprocess.run("aplay -q temp.wav", shell=True)
    except Exception as e:
        print("Erreur voix:", e)

def speak_async(text):
    threading.Thread(target=speak, args=(text,), daemon=True).start()

# =========================
# WHISPER TRANSCRIPTION
# =========================
def transcribe():
    if not os.path.exists(AUDIO_FILE):
        return ""

    try:
        result = subprocess.check_output([
            WHISPER,
            "-m", WHISPER_MODEL,
            "-f", AUDIO_FILE,
            "-l", "fr"
        ], text=True)

        print(result)

        # extraction simple du texte final
        lines = result.split("\n")
        for l in lines:
            if "]" in l:
                return l.split("]")[-1].strip().lower()

    except Exception as e:
        print("Whisper error:", e)

    return ""

# =========================
# VOICE CONTROL THREAD
# =========================
def voice_control():
    global detection_active

    print("🎤 Whisper voice control actif...")

    while True:

        # enregistrement audio
        os.system("arecord -f S16_LE -r 16000 -d 3 temp.wav")

        text = transcribe()

        if text:
            print("🗣️ Reconnu :", text)

        # ACTIVER
        if "active" in text or "detection" in text:
            detection_active = True
            speak_async("Détection activée")

        # STOP
        if "arrête" in text or "stop" in text:
            detection_active = False
            speak_async("Détection arrêtée")

        time.sleep(0.5)

# =========================
# YOLO STREAM
# =========================
def generate_frames():
    global last_time, last_counts

    while True:
        success, frame = cap.read()
        if not success:
            continue

        annotated = frame.copy()
        detected = []

        if detection_active:
            results = model(frame, imgsz=256, conf=0.65, verbose=False)

            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = model.names[cls]

                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        annotated,
                        f"{name} {conf*100:.0f}%",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    detected.append(name)

        # VOIX OBJETS
        if detected:
            counts = Counter(detected)

            if counts != last_counts and time.time() - last_time > cooldown:
                for obj, count in counts.items():

                    if obj == "personnes":
                        msg = f"{count} personne(s) détectée(s)"
                    elif obj == "voitures":
                        msg = f"{count} voiture(s) détectée(s)"
                    elif obj == "moto":
                        msg = f"{count} moto(s) détectée(s)"
                    elif obj == "chaises":
                        msg = f"{count} chaise(s) détectée(s)"
                    elif obj == "bouteille_plastique":
                        msg = f"{count} bouteille(s) détectée(s)"
                    else:
                        msg = f"{count} {obj} détecté(s)"

                    speak_async(msg)

                last_counts = counts
                last_time = time.time()

        # STATUS
        status = "ACTIVE" if detection_active else "ARRETEE"
        color = (0, 255, 0) if detection_active else (0, 0, 255)

        cv2.putText(
            annotated,
            f"DETECTION {status}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            3
        )

        _, buffer = cv2.imencode(".jpg", annotated)
        frame = buffer.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

        time.sleep(0.01)

# =========================
# FLASK ROUTES
# =========================
@app.route("/")
def index():
    return """
    <html>
    <body style="margin:0;background:black;display:flex;justify-content:center;align-items:center;height:100vh;">
        <img src="/video" style="width:80vw;height:80vh;object-fit:contain;">
    </body>
    </html>
    """

@app.route("/video")
def video():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    print("🚀 HopeVision démarré")

    speak_async("Système activé")

    threading.Thread(target=voice_control, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, threaded=True)