# Sample of voltage measurement and real-time plot using new API

import asyncio

from ebilab.api import BaseExperiment, BasePlotter, FloatField, SelectField
from ebilab.gui.controller import launch_gui
from ebilab.visa import K34411A


class VoltageMeasurement(BaseExperiment):
    name = "voltage"
    columns = ["V"]

    nplc = SelectField(
        choices=["0.001", "0.002", "0.006", "0.02", "0.06", "0.2", "1", "2", "10", "100"],
        default_index=1,
    )
    range = SelectField(
        choices=["auto", "0.1", "1", "10", "100", "1000"],
        default_index=0,
    )
    interval = FloatField(default=0.1, min=0.001, max=10.0)

    async def setup(self):
        self.logger.info("Connecting to multimeter...")
        self.multimeter = K34411A()
        self.logger.info("Connected to multimeter.")

    async def steps(self):
        while True:
            v = self.multimeter.measure_voltage(nplc=self.nplc, range=self.range)
            self.logger.debug(f"Voltage: {v}")
            yield {"V": v}
            await asyncio.sleep(self.interval)

    async def cleanup(self):
        self.logger.info("Voltage measurement finished.")


@VoltageMeasurement.register_plotter
class VoltagePlotter(BasePlotter):
    name = "voltage"

    max_voltage = FloatField(default=10.0, min=0)
    min_voltage = FloatField(default=-10.0, max=0)

    def setup(self):
        if self.fig:
            self._ax = self.fig.add_subplot(111)

    def update(self, df):
        if hasattr(self, "_ax") and not df.empty:
            self._ax.clear()

            self._ax.plot(df["t"], df["V"])
            self._ax.set_xlabel("Time / s")
            self._ax.set_ylabel("Voltage / V")
            self._ax.set_ylim(self.min_voltage, self.max_voltage)
            self._ax.grid(True)


if __name__ == "__main__":
    launch_gui([VoltageMeasurement])
