# sample of multi-thread measurement / plotting using Plotter / Experiment class
import matplotlib.pyplot as plt

from ebilab.experiment import IExperimentProtocol, IExperimentPlotter, ExperimentContext, launch_experiment
from ebilab.experiment.devices import K34411A

class ResistancePlotter(IExperimentPlotter):
    name = "simple"
    def prepare(self):
        _, self._ax = plt.subplots(1, 1, num=self.fig.number)

    def update(self, df):
        df = df.query("R < 1e20")

        self._ax.cla()
        self._ax.plot(df["t"], df["R"])
        self._ax.set_xlabel("Time / s")
        self._ax.set_ylabel("Resistance / Ohm")
        self._ax.grid()

class ContinuousResistanceMesurement(IExperimentProtocol):
    name = "resistance"
    columns = ["R"]
    plotter_classes = [ResistancePlotter]

    def steps(self, ctx: ExperimentContext, options: dict):
        multimeter = K34411A()
        while True:
            r = multimeter.measure_resistance()
            ctx.send_row({"R": r})
            ctx.loop()

if __name__ == "__main__":
    launch_experiment([ContinuousResistanceMesurement])
