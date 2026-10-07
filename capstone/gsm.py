import time
import serial
from difflib import get_close_matches

import config
from speaker import speak
from voice   import normalize


class GSMSystem:
    """
    Envoi SMS, réception SMS, correspondance contacts.
    Si le dongle GSM n'est pas branché, le système continue de fonctionner
    (détection vidéo + commandes vocales) — seules les fonctions SMS sont
    désactivées et signalées vocalement une seule fois au démarrage.
    """

    def __init__(self):
        self.connected = False
        self.ser = None

        print(f"📡 Connexion GSM sur {config.GSM_PORT}...")
        try:
            self.ser = serial.Serial(config.GSM_PORT, config.GSM_BAUD, timeout=1)
            time.sleep(2)
            self._init()
            self.connected = True
        except serial.SerialException as e:
            print(f"⚠️  GSM indisponible ({e}) — fonctions SMS désactivées")

    # --------------------------------------------------
    def _init(self):
        for cmd in [b"AT\r", b"AT+CPIN?\r", b"AT+CREG?\r",
                    b"AT+CMGF=1\r", b"AT+CNMI=2,2,0,0,0\r"]:
            self.ser.write(cmd)
            time.sleep(1)
        print("📡 GSM READY")

    # --------------------------------------------------
    def send_sms(self, number: str, message: str) -> bool:
        if not self.connected:
            print("⚠️  GSM non connecté — envoi impossible")
            return False
        try:
            print(f"📡 Envoi SMS → {number}")
            self.ser.reset_input_buffer()
            self.ser.write(b"AT\r");                           time.sleep(0.5)
            self.ser.write(b"AT+CMGF=1\r");                   time.sleep(0.5)
            self.ser.write(f'AT+CMGS="{number}"\r'.encode()); time.sleep(1.5)
            self.ser.write(message.encode());                  time.sleep(0.5)
            self.ser.write(bytes([26]))                        # CTRL+Z
            time.sleep(6)
            resp = self.ser.read_all().decode(errors="ignore")
            print("📡 RESPONSE:", resp)
            return "+CMGS" in resp or "OK" in resp
        except Exception as e:
            print("❌ GSM send_sms :", e)
            return False

    # --------------------------------------------------
    def find_contact(self, text: str):
        """Retourne (nom, numéro) ou (None, None)."""
        t     = normalize(text)
        match = get_close_matches(t, config.CONTACTS.keys(), n=1, cutoff=0.5)
        if match:
            name = match[0]
            return name, config.CONTACTS[name]
        for name in config.CONTACTS:
            if name in t:
                return name, config.CONTACTS[name]
        return None, None

    # --------------------------------------------------
    def sms_listener(self) -> None:
        """
        Thread dédié aux SMS entrants.
        Ne démarre la surveillance que si le GSM est connecté.
        """
        if not self.connected:
            print("📡 SMS listener non démarré (GSM absent)")
            return

        print("📡 SMS LISTENER READY")
        while True:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                if "+CMT:" in line:
                    msg = self.ser.readline().decode(errors="ignore").strip()
                    print("📩 SMS reçu :", msg)
                    speak(f"Nouveau message reçu : {msg}")
            except Exception as e:
                print("❌ SMS ERROR :", e)