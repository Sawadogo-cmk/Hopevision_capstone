import subprocess
import time
import sys
from pijuice import PiJuice

pijuice = PiJuice(1, 0x14)

# Ordre de défilement (change l'ordre si tu préfères)
scripts = ["sms.py", "detection.py", "lecture.py"]
index = 0
process = None

def lancer_script(nom):
    global process
    # Arrêter le précédent s'il tourne encore
    if process and process.poll() is None:
        print(f"Arrêt de {nom_precedent}")
        process.terminate()
        process.wait()
    print(f"Lancement de {nom}")
    process = subprocess.Popen([sys.executable, nom])
    return nom

print("Gestionnaire PiJuice – SW3 défile les scripts.")
print(f"Ordre : {' → '.join(scripts)}")
print("Appuie sur le bouton droit pour changer.\n")

nom_precedent = None

try:
    while True:
        ev = pijuice.status.GetButtonEvents().get('data', {})
        if ev.get('SW3') == 'PRESS':
            nom_precedent = lancer_script(scripts[index])
            index = (index + 1) % len(scripts)
            # Attendre que le bouton soit relâché
            while pijuice.status.GetButtonEvents().get('data', {}).get('SW3') == 'PRESS':
                time.sleep(0.05)
        time.sleep(0.05)
except KeyboardInterrupt:
    if process and process.poll() is None:
        process.terminate()
    print("Arrêt du gestionnaire.")