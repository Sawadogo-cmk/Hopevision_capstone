"""
Gestion de la caméra pour HopeVision AI
"""

import cv2
import threading
import time

class CameraManager:
    """Gestionnaire de caméra avec buffer thread-safe"""
    
    def __init__(self, camera_id=0, width=640, height=480):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.cap = None
        self.lock = threading.Lock()
        self.frame = None
        self.is_running = False
        
        self.initialize()
    
    def initialize(self):
        """Initialise la caméra"""
        self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2)
        
        if not self.cap.isOpened():
            raise RuntimeError("❌ Impossible d'ouvrir la caméra")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        print(f"✅ Caméra initialisée: {self.width}x{self.height}")
    
    def get_frame(self):
        """Retourne la dernière frame capturée"""
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            return None
    
    def read_frame(self):
        """Lit une frame de la caméra"""
        if self.cap and self.cap.isOpened():
            success, frame = self.cap.read()
            if success:
                with self.lock:
                    self.frame = frame
                return frame
        return None
    
    def release(self):
        """Libère les ressources de la caméra"""
        if self.cap:
            self.cap.release()
            print("📷 Caméra libérée")
    
    def __del__(self):
        self.release()