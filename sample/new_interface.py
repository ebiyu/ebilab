# sample of GUI app
import time
import random

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ebilab.experiment import IExperimentProtocol, IExperimentPlotter, ExperimentContext, launch_experiment


#  class to decide how to plot during experiment
class MyPlotter(IExperimentPlotter):
    name = "simple"
    def prepare(self):
        # this method is executed before starting experiment
        # e.g. initializing Figure
        # figure is stored in `fig` for GUI support

        self._ax = self.fig.add_subplot(111)

    def update(self, df):
        # this method is executed many times during experiment
        # df is pandas.DataFrame which has experiment data

        self._ax.cla()

        self._ax.plot(df["t"], df["v"])
        self._ax.set_xlabel("Time")
        self._ax.set_ylabel("Voltage")
        self._ax.grid()

# class to decide steps of experiment
class RandomWalkExperiment(IExperimentProtocol):
    columns = ["v", "v2"] # please specify columns to write csv file
    name = "random-walk" # filename is suffixed by datetime
    plotter_classes = [MyPlotter]

    def steps(self, ctx: ExperimentContext) -> None: # step of measurement
        v = 0
        while True: # please check self.running in every loop
            time.sleep(0.2)

            v += 1 if random.random() < 0.5 else -1

            # you can use ctx.send_row() to plot and save data
            ctx.send_row({"v": v})

            ctx.loop() # you must run ctx.loop() in every loop

if __name__ == "__main__":
    launch_experiment([RandomWalkExperiment])
    # app = GUIExperimentApp([[, [MyPlotter]], [RandomWalkExperiment, [MyPlotter, MyPlotter]]])
    # app.start()