# Sample of simple resistance measurement using new API

import asyncio

from ebilab.api import BaseExperiment, BasePlotter, FloatField, SelectField
from ebilab.gui.controller import launch_gui
from ebilab.visa import K34411A


class SimpleResistanceMeasurement(BaseExperiment):
    name = "simple-resistance"
    columns = ["R"]

    nplc = SelectField(
        choices=["0.001", "0.002", "0.006", "0.02", "0.06", "0.2", "1", "2", "10", "100"],
        default_index=1,
    )
    range = SelectField(
        choices=["auto", "1E+2", "1E+3", "1E+4", "1E+5", "1E+6", "1E+7", "1E+8", "1E+9"],
        default_index=5,
    )
    interval = FloatField(default=0.5, min=0.001, max=10.0)

    async def setup(self):
        self.logger.info("Connecting to multimeter...")
        self.multimeter = K34411A()
        self.logger.info("Connected to multimeter.")

    async def steps(self):
        while True:
            r = self.multimeter.measure_resistance(range=self.range, nplc=self.nplc)
            self.logger.info(f"Resistance: {r}")
            yield {"R": r}
            await asyncio.sleep(self.interval)

    async def cleanup(self):
        self.logger.info("Simple resistance measurement finished.")


@SimpleResistanceMeasurement.register_plotter
class SimpleResistancePlotter(BasePlotter):
    name = "simple"

    def setup(self):
        if self.fig:
            self._ax = self.fig.add_subplot(111)

    def update(self, df):
        if hasattr(self, "_ax") and not df.empty:
            self._ax.clear()

            self._ax.plot(df["t"], df["R"], "o-")
            self._ax.set_xlabel("Time / s")
            self._ax.set_ylabel("Resistance / Ohm")
            self._ax.grid(True)


if __name__ == "__main__":
    launch_gui([SimpleResistanceMeasurement])
