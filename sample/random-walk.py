# sample of GUI app
import time
import random

from ebilab.experiment import ExperimentProtocol, ExperimentPlotter, ExperimentContext, PlotterContext, launch_experiment
from ebilab.experiment.options import FloatField, SelectField

#  class to decide how to plot during experiment
class MyPlotter(ExperimentPlotter):
    name = "simple"
    def prepare(self, ctx: PlotterContext):
        # this method is executed before starting experiment
        # e.g. adding Axes to Figure
        # figure is stored in `self.fig`

        self._ax = self.fig.add_subplot(111)

    def update(self, df, ctx: PlotterContext):
        # this method is executed many times during experiment
        # df is pandas.DataFrame which has experiment data

        self._ax.cla()

        self._ax.plot(df["t"], df["v"])
        self._ax.set_xlabel("Time")
        self._ax.set_ylabel("Voltage")
        self._ax.grid()

# class to decide steps of experiment
class RandomWalkExperiment(ExperimentProtocol):
    columns = ["v", "v2"] # please specify columns to write csv file
    name = "random-walk" # filename is suffixed by datetime
    plotter_classes = [MyPlotter]

    # available in GUI
    options = {
        "initial": FloatField(default=2),
        "step": SelectField(choices=[1, 2, 4], default_index=1),
    }

    def steps(self, ctx: ExperimentContext) -> None: # step of measurement
        v = ctx.options["initial"]
        step = ctx.options["step"]
        while True:
            # you can use ctx.send_row() to plot and save data
            ctx.log(f"log: {v}")
            ctx.send_row({"v": v})

            time.sleep(0.2)
            v += step if random.random() < 0.5 else -step

            ctx.loop() # you must run ctx.loop() in every loop

if __name__ == "__main__":
    launch_experiment([RandomWalkExperiment])

