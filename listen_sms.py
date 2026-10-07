import serial

ser = serial.Serial("/dev/ttyUSB2", 115200, timeout=1)

print("📡 Listening SMS...")

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print(line)