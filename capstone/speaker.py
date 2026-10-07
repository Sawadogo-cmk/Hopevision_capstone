import subprocess
import threading

import config


def speak(text: str) -> None:
    """TTS synchrone — bloque jusqu'à la fin de la lecture."""
    try:
        cmd = f'echo "{text}" | {config.PIPER} -m {config.VOICE_MODEL} -f {config.TEMP_WAV}'
        subprocess.run(cmd, shell=True, check=False)
        subprocess.run(f"aplay -q {config.TEMP_WAV}", shell=True, check=False)
    except Exception as e:
        print("❌ Erreur speaker :", e)


def speak_async(text: str) -> None:
    """TTS non-bloquant — lance speak() dans un thread daemon."""
    threading.Thread(target=speak, args=(text,), daemon=True).start()