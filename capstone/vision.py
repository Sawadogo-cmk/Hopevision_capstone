import time
from collections import Counter

import cv2
from ultralytics import YOLO

import config
from speaker import speak_async


class VisionSystem:
    """Caméra + détection YOLO + annonces vocales."""

    def __init__(self):
        print("🔄 Chargement YOLO...")
        self.model = YOLO(config.YOLO_MODEL)
        print("✅ YOLO prêt — classes :", self.model.names)

        self.cap            = self._open_camera()
        self.detection_active = False
        self.last_time      = 0
        self.last_counts    = {}

    # --------------------------------------------------
    def _open_camera(self):
        cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        if not cap.isOpened():
            raise RuntimeError("❌ Caméra introuvable")
        print("✅ Caméra ouverte")
        return cap

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()

    # --------------------------------------------------
    def generate_frames(self):
        """Générateur MJPEG pour Flask."""
        while True:
            ok, frame = self.cap.read()
            if not ok:
                continue

            out      = frame.copy()
            detected = []

            if self.detection_active:
                detected = self._run_yolo(frame, out)

            self._maybe_announce(detected)
            self._draw_status(out)

            _, buf = cv2.imencode(".jpg", out)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buf.tobytes()
                + b"\r\n"
            )
            time.sleep(0.01)

    # --------------------------------------------------
    def _run_yolo(self, frame, out) -> list:
        results  = self.model(
            frame,
            imgsz=config.YOLO_IMGSZ,
            conf=config.YOLO_CONF,
            device=config.YOLO_DEVICE,
            verbose=False,
        )
        detected = []
        for r in results:
            for box in r.boxes:
                cls_id      = int(box.cls[0])
                conf        = float(box.conf[0])
                name        = self.model.names[cls_id]
                x1,y1,x2,y2 = map(int, box.xyxy[0])

                cv2.rectangle(out, (x1,y1), (x2,y2), (0,255,0), 2)
                cv2.putText(
                    out, f"{name} {conf*100:.0f}%",
                    (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0,255,0), 2,
                )
                detected.append(name)
        return detected

    # --------------------------------------------------
    def _maybe_announce(self, detected: list) -> None:
        if not detected:
            return
        counts = Counter(detected)
        now    = time.time()
        if counts == self.last_counts or (now - self.last_time) < config.COOLDOWN:
            return

        print("🔊 Détection :", counts)
        parts = []
        for obj, n in counts.items():
            tmpl = config.OBJECT_LABELS.get(obj)
            if tmpl:
                parts.append(tmpl[0] if n == 1 else tmpl[1].format(n=n))
            else:
                parts.append(f"{n} {obj} detectes")
        speak_async(". ".join(parts))
        self.last_counts = counts
        self.last_time   = now

    # --------------------------------------------------
    def _draw_status(self, frame) -> None:
        if self.detection_active:
            label, color = "DETECTION ACTIVE",  (0, 255, 0)
        else:
            label, color = "DETECTION ARRETEE", (0, 0, 255)
        cv2.putText(frame, label, (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)