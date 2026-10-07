# HopeVision — Structure du projet

```
hopevision/
├── main.py        ← Point d'entrée unique
├── config.py      ← Toutes les constantes (chemins, ports, mots-clés…)
├── vision.py      ← Caméra + détection YOLO + annonces vocales
├── voice.py       ← Vosk : reconnaissance vocale + commandes
├── speaker.py     ← Piper TTS : speak() et speak_async()
├── gsm.py         ← Module SMS (optionnel)
└── web.py         ← Serveur Flask + stream vidéo MJPEG
```

## Lancer le système

```bash
cd hopevision
python main.py
```

Puis ouvrir `http://<ip_raspberry>:5000` dans un navigateur.

## Activer le module GSM (SMS)

Dans `main.py`, décommenter les lignes :

```python
from gsm import GSMSystem
gsm = GSMSystem()
t_gsm = threading.Thread(target=gsm.voice_sms_loop, args=(...), daemon=True)
t_gsm.start()
```

## Modifier les paramètres

Tout se configure dans **config.py** :
- `AUDIO_DEVICE` : index du micro
- `GSM_PORT` : port série du module GSM
- `COOLDOWN` : délai entre deux annonces vocales
- `CONTACTS` : carnet d'adresses pour les SMS
- `ACTIVATE_KEYWORDS` / `STOP_KEYWORDS` : mots déclencheurs

## Dépendances

```bash
pip install ultralytics opencv-python flask vosk sounddevice pyserial
```