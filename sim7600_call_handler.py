import serial
import time
import os

PORT = "/dev/ttyUSB2"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)

def send(cmd, delay=1):
    print("➡️", cmd)
    ser.write((cmd + "\r\n").encode())
    time.sleep(delay)

    while ser.in_waiting:
        print("⬅️", ser.readline().decode(errors="ignore").strip())

print("📞 SIM7600 Call Handler prêt")

send("AT+CLIP=1")

print("🎧 En attente d'appel...")

while True:
    line = ser.readline().decode(errors="ignore").strip()

    if line:
        print("📡", line)

        if "RING" in line:
            print("📞 Appel détecté → décroche")
            send("ATA")

            print("🎤 Appel décroché, audio ON")

            os.system("arecord -D plughw:3,0 -f S16_LE -r 8000 | aplay -D plughw:2,0 &")

        if "NO CARRIER" in line:
            print("📴 Appel terminé")

            os.system("pkill arecord")
            os.system("pkill aplay")