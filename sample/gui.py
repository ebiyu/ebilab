# sample of GUI app
import time
import random

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ebilab.experiment import Plotter, Experiment
from ebilab.experiment.gui import GUIExperimentApp

# class to decide steps of experiment
class RandomWalkExperiment(Experiment):
    columns = ["v", "v2"] # please specify columns to write csv file
    filename = "random-walk" # filename is suffixed by datetime

    def steps(self): # step of measurement
        v = 0
        while self.running: # please check self.running in every loop
            time.sleep(0.2)

            # you can use self.send_row() to plot and save data
            v += 1 if random.random() < 0.5 else -1
            self.send_row({"v": v})

# (Optional) class to decide how to plot during experiment
class MyPlotter(Plotter):
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

if __name__ == "__main__":
    app = GUIExperimentApp([[RandomWalkExperiment, [MyPlotter]], [RandomWalkExperiment, [MyPlotter, MyPlotter]]])
    app.start()
