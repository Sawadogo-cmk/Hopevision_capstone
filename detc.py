from ultralytics import YOLO
import cv2
from flask import Flask, Response
import time
import subprocess
import os
import threading
from collections import Counter

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

# =========================
# YOLO MODEL
# =========================
print("🔄 Chargement du modèle...")
model = YOLO("best.pt")
print("✅ Modèle prêt")
print("📦 Classes :", model.names)

# =========================
# VOIX (PIPER)
# =========================
PIPER = os.path.expanduser("~/piper_bin/piper/piper")
VOICE_MODEL = os.path.expanduser("~/HopeVision/fr_FR-siwis-medium.onnx")

def speak_async(text):
    def run():
        try:
            cmd = f'echo "{text}" | {PIPER} -m {VOICE_MODEL} -f temp.wav'
            subprocess.run(cmd, shell=True)
            subprocess.run("aplay -q temp.wav", shell=True)
        except Exception as e:
            print("Erreur voix :", e)

    threading.Thread(target=run, daemon=True).start()

# =========================
# CAMERA
# =========================
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("❌ Caméra introuvable")
    exit()

# =========================
# VIDEO WRITER (ENREGISTREMENT)
# =========================
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(
    "output.avi",
    fourcc,
    20.0,
    (640, 480)
)

print("🎥 Enregistrement vidéo activé (output.avi)")

# =========================
# VARIABLES
# =========================
last_time = 0
cooldown = 4
last_counts = {}

# =========================
# GENERATE FRAMES
# =========================
def generate_frames():
    global last_time, last_counts

    while True:
        success, frame = cap.read()
        if not success:
            continue

        results = model(frame, imgsz=256, conf=0.80, device="cpu", verbose=False)

        annotated_frame = frame.copy()
        detected_objects = []

        # =========================
        # DETECTION
        # =========================
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                name = model.names[cls_id]

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # Dessin
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{name} {conf*100:.0f}%"
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

                detected_objects.append(name)

        # =========================
        # ENREGISTREMENT VIDEO 🎥
        # =========================
        out.write(annotated_frame)

        # =========================
        # VOIX INTELLIGENTE
        # =========================
        if detected_objects:
            counts = Counter(detected_objects)

            if counts != last_counts and (time.time() - last_time > cooldown):
                print("🔊 Détection :", counts)

                for obj, count in counts.items():

                    if obj == "personnes":
                        text = "Une personne détectée" if count == 1 else f"{count} personnes détectées"

                    elif obj == "voitures":
                        text = "Une voiture détectée" if count == 1 else f"{count} voitures détectées"

                    elif obj == "moto":
                        text = "Une moto détectée" if count == 1 else f"{count} motos détectées"

                    elif obj == "chaises":
                        text = "Une chaise détectée" if count == 1 else f"{count} chaises détectées"

                    elif obj == "bouteille_plastique":
                        text = "Une bouteille détectée" if count == 1 else f"{count} bouteilles détectées"

                    else:
                        text = f"{count} {obj} détectés"

                    speak_async(text)

                last_counts = counts
                last_time = time.time()

        # =========================
        # STREAM VIDEO
        # =========================
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.01)

# =========================
# UI WEB
# =========================
@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>HopeVision AI</title>
            <style>
                body {
                    margin: 0;
                    background: black;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }

                img {
                    width: 80vw;
                    height: 80vh;
                    object-fit: contain;
                    border-radius: 12px;
                    box-shadow: 0 0 25px rgba(0,255,0,0.3);
                }
            </style>
        </head>
        <body>
            <img src="/video">
        </body>
    </html>
    """

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# =========================
# CLEAN EXIT
# =========================
def cleanup():
    print("🛑 Arrêt du système...")
    cap.release()
    out.release()
    cv2.destroyAllWindows()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    try:
        print("🚀 HopeVision démarré")
        speak_async("Système activé")
        app.run(host="0.0.0.0", port=5000, threaded=True)

    except KeyboardInterrupt:
        cleanup()