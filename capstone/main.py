"""
HopeVision — main.py
====================
Lancement : python main.py

Le système fonctionne MEME SANS dongle GSM branché.
Dans ce cas, seules les fonctions SMS sont désactivées ;
la détection vidéo et les commandes vocales activer/arrêter
continuent normalement.

Threads au démarrage :
  [daemon] Flask        — stream vidéo sur http://0.0.0.0:5000
  [daemon] SMS listener — annonce vocale des SMS entrants (si GSM connecté)
  [main  ] Boucle vocale — détection YOLO + envoi SMS

Commandes vocales :
  "activer"   → lance la détection YOLO
  "arrêter"   → stoppe la détection YOLO
  "envoie un message" / "sms" → dialogue pour envoyer un SMS (si GSM connecté)
"""

import signal
import sys
import threading

import config
from vision  import VisionSystem
from gsm     import GSMSystem
from voice   import unified_voice_loop
from speaker import speak_async
import web


def main():
    print("🚀 HopeVision démarré")

    # ── Initialisation ──────────────────────────────────
    vision = VisionSystem()
    gsm    = GSMSystem()   # ne plante jamais, même sans dongle
    web.init_web(vision)

    # ── Bienvenue (adaptée selon dispo GSM) ─────────────
    if gsm.connected:
        speak_async(
            "Système activé. Bienvenue sur HopeVision. "
            "Dites activer pour lancer la détection, "
            "arrêter pour la stopper, "
            "ou envoie un message pour envoyer un SMS."
        )
    else:
        speak_async(
            "Système activé. Bienvenue sur HopeVision. "
            "Dites activer pour lancer la détection, "
            "ou arrêter pour la stopper. "
            "Le module SMS n'est pas disponible."
        )

    # ── Thread Flask (non-bloquant) ─────────────────────
    threading.Thread(target=web.run, daemon=True).start()
    print(f"🌐 Flask sur http://{config.FLASK_HOST}:{config.FLASK_PORT}")

    # ── Thread SMS entrants (seulement si GSM connecté) ─
    if gsm.connected:
        threading.Thread(target=gsm.sms_listener, daemon=True).start()
        print("📡 SMS listener démarré")
    else:
        print("📡 SMS listener ignoré (GSM non connecté)")

    # ── CTRL+C propre ───────────────────────────────────
    def _on_exit(sig, frame):
        print("\n🛑 Arrêt...")
        vision.release()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _on_exit)
    signal.signal(signal.SIGTERM, _on_exit)

    # ── Boucle vocale — thread principal (bloquant) ─────
    unified_voice_loop(vision, gsm)


if __name__ == "__main__":
    main()