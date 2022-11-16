# Sample of simple resistance measurement

from time import sleep

from ebilab.experiment.devices import K34411A

multimeter = K34411A()

with open("file.csv", "w") as f:
    while True:
        r = multimeter.measure_resistance(range="1E+6", nplc="0.002")
        print(r)
        f.write(f"{r}\n")
        sleep(0.5)
