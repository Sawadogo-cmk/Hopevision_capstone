#!/usr/bin/env python3
"""
detection.py – Détection d'objets YOLO + annonces vocales (toujours actif)
Améliorations :
- Filtre de stabilité (3 frames avant annonce)
- Callback audio non bloquant
- Timeout sur la synthèse vocale
- Reconnexion automatique de la caméra
- Détection active en permanence (pas de commande vocale d'activation)
"""

import os
import sys
import json
import time
import threading
import queue
import subprocess
from collections import Counter

import cv2
import numpy as np
from flask import Flask, Response

# =========================
# YOLO
# =========================
from ultralytics import YOLO

# =========================
# VOSK (reconnaissance vocale)
# =========================
from vosk import Model, KaldiRecognizer
import sounddevice as sd

# =========================
# CONFIGURATION GÉNÉRALE
# =========================
PIPER = os.path.expanduser("~/piper_bin/piper/piper")
VOICE_MODEL = os.path.expanduser("~/HopeVision/fr_FR-siwis-medium.onnx")

VOSK_MODEL_PATH = "vosk-model-small-fr-0.22"
DEVICE_ID = 1
REPEAT_INTERVAL = 5               # secondes entre rappels pour un même objet
FLASK_PORT = 5000

# =========================
# CAMÉRA (détection automatique)
# =========================
CAMERAS = [
    "/dev/v4l/by-id/usb-WNDZ-8M_Lightburn_Camera_200901010001-video-index0",
    "/dev/v4l/by-id/usb-HD_USB_Camera_HD_USB_Camera_2020070302-video-index0"
]


def trouver_camera():
    """
    Parcourt la liste des caméras et retourne la première qui s'ouvre.
    """
    for camera in CAMERAS:
        print("🔍 Test caméra :", camera)
        cap = cv2.VideoCapture(camera, cv2.CAP_V4L2)
        if cap.isOpened():
            print("✅ Caméra utilisée :", camera)
            return cap
        cap.release()
    return None


# Initialisation de la caméra
cap = trouver_camera()
if cap is None:
    print("❌ Aucune caméra trouvée")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# =========================
# CHARGEMENT DU MODÈLE YOLO
# =========================
print("🔄 Chargement du modèle YOLO...")
model = YOLO("best.pt")
print("✅ Modèle YOLO prêt")
print("📦 Classes :", model.names)

# =========================
# VARIABLES GLOBALES
# =========================
tracked_objects = {}              # {nom: {"last_announced": float, "count": int}}
detection_active = True           # <-- DÉTECTION ACTIVE EN PERMANENCE

# --- Filtre de stabilité ---
STABILITY_FRAMES = 2             # nombre de frames consécutives avant annonce
pending_objects = {}              # {nom: compteur de frames vues d'affilée}

# =========================
# SEUILS DE CONFIANCE PAR CLASSE
# =========================
CONF_PAR_CLASSE = {
    "voitures": 0.85,
    "chaises": 0.60,
}
CONF_DEFAUT = 0.65


def conf_minimum(nom_classe):
    """
    Retourne le seuil de confiance minimum pour une classe donnée.
    """
    return CONF_PAR_CLASSE.get(nom_classe, CONF_DEFAUT)


# =========================
# MOTS CLÉS VOCAUX (plus besoin d'activer/désactiver)
# =========================
# On les garde vides mais le code de voice_control reste simplifié
# Aucun mot-clé n'est défini ici.

# =========================
# NOMS POUR LA VOIX (singulier / pluriel)
# =========================
NOMS_VOIX = {
    "personnes": ("Une personne", "personnes"),
    "voitures": ("Une voiture", "voitures"),
    "moto": ("Une moto", "motos"),
    "chaises": ("Une chaise", "chaises"),
    "bouteille_plastique": ("Une bouteille", "bouteilles"),
}


# =========================
# NORMALISATION TEXTE
# =========================
def normalize_text(text):
    """
    Supprime les accents et met en minuscule pour faciliter la reconnaissance.
    """
    text = text.lower().strip()
    replacements = {
        "é": "e", "è": "e", "ê": "e",
        "à": "a", "ù": "u", "ô": "o", "î": "i"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


# =========================
# SYNTHÈSE VOCALE (Piper, file d'attente, avec timeout)
# =========================
tts_queue = queue.Queue()


def tts_worker():
    """
    Thread qui traite les messages vocaux les uns après les autres.
    Un timeout est appliqué pour éviter tout blocage.
    """
    while True:
        text = tts_queue.get()
        if text is None:
            continue
        try:
            temp_file = "temp_voice.wav"
            # Génération du fichier audio avec Piper
            cmd = f'echo "{text}" | {PIPER} -m {VOICE_MODEL} -f {temp_file}'
            subprocess.run(cmd, shell=True, capture_output=True, timeout=15)
            # Lecture du fichier audio (timeout de 8 secondes)
            subprocess.run(f"aplay -q {temp_file}", shell=True, timeout=8)
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print("❌ Erreur voix :", e)
        finally:
            tts_queue.task_done()


def speak_async(text):
    """
    Ajoute un message à la file d'attente vocale.
    """
    tts_queue.put(text)


# =========================
# CONTRÔLE VOCAL (simplifié, ne gère plus l'activation)
# =========================
def voice_control():
    """
    Thread de reconnaissance vocale.
    N'intervient plus sur l'activation, il peut rester pour d'autres commandes futures.
    """
    # On conserve la structure audio non bloquante mais on ne fait rien des mots reconnus.
    device_id = DEVICE_ID
    device_info = sd.query_devices(device_id, 'input')
    samplerate = int(device_info['default_samplerate'])
    print(f"🎤 Micro : {device_info['name']} ({samplerate} Hz)")

    recognizer = KaldiRecognizer(Model(VOSK_MODEL_PATH), samplerate)

    audio_queue = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        audio_queue.put(bytes(indata))

    print("🎤 Écoute vocale active (mode passif)...")

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        device=device_id,
        dtype='int16',
        channels=1,
        callback=audio_callback
    ):
        while True:
            try:
                data = audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = normalize_text(result.get("text", ""))
                if text:
                    print("🗣️ Reconnu :", text)
                    # Aucune action, on ignore


# =========================
# CONSTRUCTION DU MESSAGE VOCAL
# =========================
def build_message(name, count):
    """
    Formate le message vocal à partir du nom de l'objet et de son nombre.
    """
    singulier, pluriel = NOMS_VOIX.get(name, (f"Un {name}", f"{name}"))
    if count == 1:
        return f"{singulier} détectée"
    else:
        return f"{count} {pluriel} détectés"


# =========================
# GÉNÉRATION DU FLUX VIDÉO (détection toujours active)
# =========================
def generate_frames():
    """
    Boucle principale de capture vidéo, détection YOLO, annonces vocales.
    Détection active en permanence.
    """
    global tracked_objects, pending_objects, cap

    fail_count = 0

    while True:
        try:
            success, frame = cap.read()
            if not success:
                fail_count += 1
                if fail_count > 30:
                    print("⚠️ Perte de la caméra, tentative de reconnexion...")
                    cap.release()
                    time.sleep(2)
                    new_cap = trouver_camera()
                    if new_cap is None:
                        print("❌ Échec reconnexion, arrêt du flux.")
                        break
                    cap = new_cap
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    fail_count = 0
                time.sleep(0.1)
                continue
            fail_count = 0

            annotated_frame = frame.copy()
            current_frame_objects = {}

            # Détection YOLO (toujours active)
            results = model(frame, imgsz=256, conf=CONF_DEFAUT, device="cpu", verbose=False)
            names_seen = []

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = model.names[cls_id]

                    if conf < conf_minimum(name):
                        continue

                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"{name} {conf*100:.0f}%"
                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    names_seen.append(name)

            counts = Counter(names_seen)
            for name, count in counts.items():
                current_frame_objects[name] = count

            # Filtre de stabilité
            for name in current_frame_objects:
                pending_objects[name] = pending_objects.get(name, 0) + 1
            for name in list(pending_objects.keys()):
                if name not in current_frame_objects:
                    del pending_objects[name]

            confirmed_objects = {name for name, cnt in pending_objects.items() if cnt >= STABILITY_FRAMES}

            # Annonces
            now = time.time()
            current_names = set(confirmed_objects)
            previous_names = set(tracked_objects.keys())

            for name in (current_names - previous_names):
                count = current_frame_objects.get(name, 1)
                speak_async(build_message(name, count))
                tracked_objects[name] = {"last_announced": now, "count": count}

            for name in (current_names & previous_names):
                count = current_frame_objects[name]
                tracked_objects[name]["count"] = count
                if now - tracked_objects[name]["last_announced"] > REPEAT_INTERVAL:
                    speak_async(build_message(name, count))
                    tracked_objects[name]["last_announced"] = now

            for name in list(previous_names - current_names):
                del tracked_objects[name]

            # Affichage état
            state_text = "DETECTION ACTIVE"
            cv2.putText(annotated_frame, state_text, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

            # Streaming
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n'
                   + frame_bytes + b'\r\n')

        except Exception as e:
            print("⚠️ Erreur dans generate_frames :", e)
            time.sleep(0.5)

        time.sleep(0.01)


# =========================
# FLASK
# =========================
app = Flask(__name__)


@app.route('/')
def index():
    return """
    <html>
    <head><title>HopeVision AI</title>
    <style>
        body{ margin:0; background:black; display:flex;
              justify-content:center; align-items:center; height:100vh; }
        img{ width:80vw; height:80vh; object-fit:contain;
             border-radius:12px; box-shadow:0 0 25px rgba(0,255,0,0.3); }
    </style></head>
    <body><img src="/video"></body>
    </html>
    """


@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def cleanup():
    print("🛑 Arrêt du système...")
    if cap:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        print("🚀 HopeVision démarré (détection active en continu)")
        threading.Thread(target=tts_worker, daemon=True).start()
        # Message d'accueil simplifié
        speak_async("Détection d'objets activée. Je vous décris ce que je vois.")
        threading.Thread(target=voice_control, daemon=True).start()
        app.run(host="0.0.0.0", port=FLASK_PORT, threaded=True)
    except KeyboardInterrupt:
        cleanup()