import serial
import time

PORT = "/dev/ttyUSB2"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)

def send_at(cmd, delay=1):
    print(f"\n➡️ {cmd}")
    ser.write((cmd + "\r\n").encode())
    time.sleep(delay)

    while ser.in_waiting:
        response = ser.readline().decode(errors="ignore").strip()
        if response:
            print("⬅️", response)

print("📡 TEST SIM7600 VOICE + AUDIO + CONTACTS")

# =========================
# BASIC CHECKS
# =========================
send_at("AT")
send_at("AT+CPIN?")
send_at("AT+CSQ")
send_at("AT+COPS?")

# =========================
# CONTACTS SIM
# =========================
send_at("AT+CPBS=\"SM\"")
send_at("AT+CPBR=1,50")

# =========================
# AUDIO SETUP (IMPORTANT)
# =========================

# volume appel (important)
send_at("AT+CLVL=100")

# route audio vers handset / headset (selon module)
send_at("AT+CSDVC=1")

# =========================
# CALL TEST MODE
# =========================

print("\n📞 READY FOR CALL TEST")

# exemple appel (décommenter si tu veux tester direct)
# send_at('ATD+22770012389;')

# raccrocher
# send_at("ATH")

# =========================
# USB MODE
# =========================
send_at("AT+CUSBPIDSWITCH=9001,1,1")

ser.close()