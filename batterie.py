from pijuice import PiJuice

pijuice = PiJuice(1, 0x14)
print(pijuice.status.GetStatus())