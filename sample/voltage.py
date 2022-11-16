# Sample of voltage measurement and real-time plot in single thread

from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from ebilab.experiment.devices import K34411A

class VoltagePlotter:
    _fig: Figure
    _line1: Line2D
    def __init__(self):
        self._fig, self._ax = plt.subplots(1, 1)
        plt.pause(0.01)

    def update(self, df: pd.DataFrame):
        self._ax.cla()

        self._ax.plot(df["t"], df["V"])
        self._ax.set_xlabel("Time")
        self._ax.set_ylabel("Voltage")
        self._ax.grid()

        plt.gcf().canvas.draw_idle()
        plt.gcf().canvas.flush_events()

if __name__ == "__main__":
    multimeter = K34411A()
    plotter = VoltagePlotter()
    data = []
    started_at = datetime.now()
    while True:
        v = multimeter.measure_voltage(nplc="0.002")
        t = (datetime.now() - started_at).total_seconds()
        print(v)
        data.append({"t": t, "V": v})
        plotter.update(pd.DataFrame(data))
