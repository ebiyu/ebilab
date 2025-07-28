# sample of GUI app
import asyncio
import random

import matplotlib.pyplot as plt

from ebilab.api import BaseExperiment, BasePlotter, FloatField, SelectField
from ebilab.gui.controller import launch_gui
from ebilab.visa import K34411A

class K34465A(K34411A):
    _idn_pattern = "34465A"

class Experiment(BaseExperiment):
    columns = ["R"]
    name = "r-continuous"
    nplc = SelectField(
        choices=["0.001", "0.002", "0.006", "0.02", "0.06", "0.2", "1", "2", "10", "100"],
        default_index=3,
    )
    range = SelectField(
        choices=["auto", "1E+2", "1E+3", "1E+4", "1E+5", "1E+6", "1E+7", "1E+8", "1E+9"],
        default_index=0,
    )

    async def setup(self):
        self.logger.info("Connecting to multimeter...")
        self.multimeter = K34465A()
        self.logger.info("Connected to multimeter.")

    async def steps(self):
        while True:
            R = self.multimeter.measure_resistance(nplc=self.nplc, range=self.range)
            yield {"R": R}


@Experiment.register_plotter
class ContinuousResistancePlotter(BasePlotter):
    name = "simple"

    duration = FloatField(default=60, min=0, max=1e6)
    max_resistance = FloatField(default=1e3, min=0)

    def setup(self):
        self._ax = self.fig.add_subplot(111)

    def update(self, df):
        with plt.rc_context(
            {
                "lines.linestyle": "none",
                "lines.marker": ".",
            }
        ):
            t_max = df.max()["t"]
            t_min = t_max - self.duration
            df = df.query(f"t > {t_min}")
            self._ax.cla()
            self._ax.plot(df["t"], df["R"])
            self._ax.set_xlabel("Time [s]")
            self._ax.set_ylabel("Resistance [Ohm]")
            self._ax.set_xlim(t_min, t_max)
            self._ax.set_ylim(0, self.max_resistance)
            self._ax.grid()


if __name__ == "__main__":
    # Launch the GUI application
    launch_gui([Experiment])
