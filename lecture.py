#!/usr/bin/env python3
"""
lecture.py – OCR vocal + flux vidéo (HopeVision)
Dites "lis", "regarde", "lecture" pour capturer et lire le texte visible.
Améliorations : détection de texte réelle, confiance Tesseract, anti-bruit.
"""

import os, re, sys, json, time, threading, queue, subprocess, argparse
import cv2, pytesseract
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from flask import Flask, Response, render_template_string

# ---------------------------
# CONFIG
# ---------------------------
PIPER        = os.path.expanduser("~/piper_bin/piper/piper")
VOICE_MODEL  = os.path.expanduser("~/HopeVision/fr_FR-siwis-medium.onnx")
TESSERACT    = "/usr/bin/tesseract"
pytesseract.pytesseract.tesseract_cmd = TESSERACT

VOSK_MODEL   = "vosk-model-small-fr-0.22"
DEVICE_ID    = 1
OCR_COOLDOWN = 5
FLASK_PORT   = 5001

# Vérifier la langue française Tesseract
try:
    langs = subprocess.check_output([TESSERACT, "--list-langs"], text=True)
    if "fra" not in langs:
        print("⚠️  Installation tesseract-ocr-fra...")
        subprocess.run("sudo apt install tesseract-ocr-fra -y", shell=True)
except:
    pass

# ---------------------------
# OBJETS PARTAGÉS
# ---------------------------
cap = None
latest_frame = None
tts_queue = queue.Queue()
ocr_result  = ""
lock = threading.Lock()
stop_event = threading.Event()

# ---------------------------
# SYNTHÈSE VOCALE
# ---------------------------
def _tts_worker():
    while True:
        txt = tts_queue.get()
        if txt is None: continue
        try:
            tmp = "temp_lecture.wav"
            subprocess.run(f'echo "{txt}" | {PIPER} -m {VOICE_MODEL} -f {tmp}',
                           shell=True, capture_output=True, timeout=15)
            subprocess.run(f"aplay -q {tmp}", shell=True, timeout=15)
        except Exception as e:
            print(f"❌ Erreur voix : {e}")
        finally:
            tts_queue.task_done()

threading.Thread(target=_tts_worker, daemon=True).start()

def lire_texte(texte):
    if texte and texte.strip():
        tts_queue.put(texte.strip())

def speak_now(texte):
    if not texte or not texte.strip(): return
    try:
        tmp = "temp_now.wav"
        subprocess.run(f'echo "{texte}" | {PIPER} -m {VOICE_MODEL} -f {tmp}',
                       shell=True, capture_output=True, timeout=15)
        subprocess.run(f"aplay -q {tmp}", shell=True, timeout=15)
    except: pass

# ---------------------------
# CAMÉRA + CAPTURE CONTINUE
# ---------------------------
def init_camera():
    global cap
    candidates = [
        "/dev/v4l/by-id/usb-WNDZ-8M_Lightburn_Camera_200901010001-video-index0",
        "/dev/v4l/by-id/usb-HD_USB_Camera_HD_USB_Camera_2020070302-video-index0"
    ]
    for cam in candidates:
        c = cv2.VideoCapture(cam, cv2.CAP_V4L2)
        if c.isOpened():
            c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap = c
            print(f"✅ Caméra : {cam}")
            return True
    return False

def capture_loop():
    global latest_frame
    while not stop_event.is_set():
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                with lock:
                    latest_frame = frame.copy()
        time.sleep(0.03)

# ---------------------------
# DÉTECTION DE ZONES DE TEXTE
# ---------------------------
def detect_text_regions(gray_image):
    """Retourne True si au moins une zone rectangulaire de texte est détectée."""
    # Binarisation simple pour séparer le texte du fond
    _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Dilater pour connecter les lettres proches
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    # Trouver les contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Filtrer les petites zones (bruit)
    min_area = 100  # pixels² minimum
    text_boxes = 0
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 20 and h > 10 and w * h > min_area:
            text_boxes += 1
    return text_boxes > 0

# ---------------------------
# OCR AMÉLIORÉ (avec confiance)
# ---------------------------
last_ocr_time = 0

def ocr_and_read():
    global last_ocr_time, ocr_result
    now = time.time()
    if now - last_ocr_time < OCR_COOLDOWN:
        lire_texte("Patientez quelques secondes.")
        return
    last_ocr_time = now

    with lock:
        if latest_frame is None:
            lire_texte("Aucune image disponible.")
            return
        frame = latest_frame.copy()

    print("📸 OCR en cours...")

    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Vérifier si l'image semble contenir du texte
        if not detect_text_regions(gray):
            lire_texte("Aucun texte visible.")
            ocr_result = ""
            return

        # Prétraitement plus doux
        # Augmentation du contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        # Légère réduction de bruit
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)

        # Configuration Tesseract : mode bloc de texte, français, avec données de confiance
        config = '--psm 6 -l fra'
        data = pytesseract.image_to_data(denoised, config=config, output_type=pytesseract.Output.DICT)

        # Filtrer les mots avec une confiance > 60
        words = []
        for i, word in enumerate(data['text']):
            conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0
            if word.strip() and conf > 60:
                words.append(word.strip())

        # Reconstituer des lignes à partir des positions (optionnel mais plus lisible)
        # Ici on assemble simplement les mots dans l'ordre de lecture
        text = ' '.join(words)

        # Nettoyage final
        text = re.sub(r'\s+', ' ', text).strip()
        # Vérifier qu'il y a au moins 2 lettres alphabétiques
        if len(re.sub(r'[^a-zA-Z]', '', text)) < 2:
            text = ""

        if text:
            print(f"📖 Texte : {text}")
            lire_texte(text)
            ocr_result = text
        else:
            lire_texte("Aucun texte lisible détecté.")
            ocr_result = ""

    except Exception as e:
        print(f"❌ Erreur OCR : {e}")
        lire_texte("Erreur lors de la lecture optique.")
        ocr_result = ""

# ---------------------------
# FLASK
# ---------------------------
app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html><head><title>HopeVision OCR</title>
<style>
    body{ margin:0; background:#111; display:flex; flex-direction:column; align-items:center; }
    img{ max-width:90vw; max-height:80vh; border-radius:12px; box-shadow:0 0 25px #0f0; margin-top:20px; }
    .info{ color:#0f0; font-family:monospace; margin-top:10px; text-align:center; }
</style></head><body>
    <img src="/video_feed">
    <div class="info">🗣️ Dites "lis", "regarde" ou "lecture" pour lire le texte à l'écran</div>
</body></html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

def gen_video():
    while True:
        with lock:
            frame = latest_frame.copy() if latest_frame is not None else None
        if frame is not None:
            # Afficher le dernier texte OCR détecté (s'il y en a un)
            if ocr_result:
                y0 = 30
                for i, line in enumerate(ocr_result.split('\n')[:5]):
                    cv2.putText(frame, line, (10, y0 + i*25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(gen_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

def start_flask(port=FLASK_PORT):
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)

# ---------------------------
# COMMANDE VOCALE
# ---------------------------
def voice_loop():
    try:
        info = sd.query_devices(DEVICE_ID, 'input')
    except:
        print(sd.query_devices())
        sys.exit(1)
    sr = int(info['default_samplerate'])
    print(f"🎤 Micro : {info['name']} ({sr} Hz)")

    model = Model(VOSK_MODEL)
    grammar = json.dumps(["lis", "lit", "lecture", "regarde", "vois", "texte", "[unk]"])
    rec = KaldiRecognizer(model, sr, grammar)

    speak_now("Système de lecture visuelle prêt. Dites 'lis' pour analyser le texte.")
    with sd.RawInputStream(samplerate=sr, blocksize=8000, device=DEVICE_ID,
                           dtype='int16', channels=1) as stream:
        while not stop_event.is_set():
            data, _ = stream.read(8000)
            if rec.AcceptWaveform(bytes(data)):
                res = json.loads(rec.Result())
                txt = res.get("text", "").lower()
                if any(w in txt for w in ["lis", "lit", "lecture", "regarde", "vois"]):
                    threading.Thread(target=ocr_and_read, daemon=True).start()

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=FLASK_PORT, help="Port Flask")
    args = p.parse_args()

    print("🚀 Démarrage lecture OCR + vidéo")
    if not init_camera():
        print("❌ Caméra introuvable")
        sys.exit(1)

    threading.Thread(target=capture_loop, daemon=True).start()
    threading.Thread(target=start_flask, args=(args.port,), daemon=True).start()
    print(f"🌐 Flux : http://localhost:{args.port}")

    try:
        voice_loop()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt")
    finally:
        stop_event.set()
        if cap: cap.release()
        cv2.destroyAllWindows()