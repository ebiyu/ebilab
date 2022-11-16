# sample of multi-thread measurement / plotting using Plotter / Experiment class
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ebilab.experiment.core import Plotter, Experiment
from ebilab.experiment.devices import K34411A

class ContinuousResistanceMesurement(Experiment):
    columns = ["R"]
    filename = "resistance"

    def steps(self):
        multimeter = K34411A()
        while self.running:
            r = multimeter.measure_resistance()
            self.send_row({"R": r})

class ResistancePlotter(Plotter):
    _fig: Figure

    def prepare(self):
        self._fig, self._ax = plt.subplots(1, 1)

    def update(self, df):
        df = df.query("R < 1e20")

        self._ax.cla()

        self._ax.plot(df["t"], df["R"])
        self._ax.set_xlabel("Time / s")
        self._ax.set_ylabel("Resistance / Ohm")
        self._ax.grid()

if __name__ == "__main__":
    experiment = ContinuousResistanceMesurement()
    experiment.plotter = ResistancePlotter()
    experiment.start()
