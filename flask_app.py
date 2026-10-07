"""
Serveur web Flask pour HopeVision AI
"""

from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

# Références globales (seront initialisées par init_flask)
camera_manager = None
detection_manager = None
speaker_manager = None

def init_flask(camera, detection, speaker):
    """Initialise les références des composants"""
    global camera_manager, detection_manager, speaker_manager
    camera_manager = camera
    detection_manager = detection
    speaker_manager = speaker

def generate_frames():
    """Générateur de frames pour le streaming vidéo"""
    while True:
        # Lire la frame de la caméra
        frame = camera_manager.read_frame()
        
        if frame is None:
            continue
        
        # Appliquer la détection
        annotated_frame, _ = detection_manager.detect(frame)
        
        # Ajouter l'état de la détection
        status = "ACTIVE" if detection_manager.is_active else "ARRETEE"
        color = (0, 255, 0) if detection_manager.is_active else (0, 0, 255)
        
        cv2.putText(
            annotated_frame,
            f"DETECTION {status}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1, color, 3
        )
        
        # Encoder en JPEG
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.01)

@app.route('/')
def index():
    """Page d'accueil avec le flux vidéo"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>HopeVision AI</title>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: #0a0a0a;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .container {
                text-align: center;
                padding: 20px;
            }
            h1 {
                color: #00ff00;
                margin-bottom: 20px;
                font-size: 2.5em;
                text-shadow: 0 0 10px rgba(0,255,0,0.5);
            }
            .video-container {
                display: inline-block;
                border: 3px solid #00ff00;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 0 30px rgba(0,255,0,0.3);
                background: #000;
            }
            img {
                display: block;
                max-width: 90vw;
                max-height: 80vh;
                object-fit: contain;
            }
            .status {
                color: #888;
                margin-top: 15px;
                font-size: 0.9em;
            }
            @keyframes pulse {
                0% { box-shadow: 0 0 30px rgba(0,255,0,0.3); }
                50% { box-shadow: 0 0 50px rgba(0,255,0,0.5); }
                100% { box-shadow: 0 0 30px rgba(0,255,0,0.3); }
            }
            .video-container {
                animation: pulse 2s infinite;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 HopeVision AI</h1>
            <div class="video-container">
                <img src="/video" alt="Flux vidéo">
            </div>
            <p class="status">🟢 Système en ligne - Dites "active" ou "arrête"</p>
        </div>
    </body>
    </html>
    """

@app.route('/video')
def video():
    """Route pour le flux vidéo"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/status')
def status():
    """Route pour vérifier le statut"""
    return {
        'detection_active': detection_manager.is_active if detection_manager else False,
        'status': 'online'
    }