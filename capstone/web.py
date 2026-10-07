from flask import Flask, Response

import config

app     = Flask(__name__)
_vision = None


def init_web(vision_system) -> None:
    global _vision
    _vision = vision_system


@app.route("/")
def index():
    return """
    <html>
    <head>
        <title>HopeVision AI</title>
        <style>
            body { margin:0; background:#000;
                   display:flex; justify-content:center;
                   align-items:center; height:100vh; }
            img  { width:80vw; height:80vh; object-fit:contain;
                   border-radius:12px;
                   box-shadow:0 0 25px rgba(0,255,0,0.3); }
        </style>
    </head>
    <body><img src="/video"></body>
    </html>
    """


@app.route("/video")
def video():
    return Response(
        _vision.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


def run() -> None:
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, threaded=True)