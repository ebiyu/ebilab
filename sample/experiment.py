# sample of multi-thread plotting using Plotter / Experiment class
import time
import random

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ebilab.experiment.core import Plotter, Experiment

# class to decide steps of experiment
class MyExperiment(Experiment):
    columns = ["v"] # please specify columns to write csv file
    filename = "my-experiment" # filename is suffixed by datetime

    def steps(self): # step of measurement
        while self.running: # please check self.running in every loop
            time.sleep(0.2)

            # you can use self.send_row() to plot and save data
            self.send_row({"v": random.random()})

# (Optional) class to decide how to plot during experiment
class MyPlotter(Plotter):
    _fig: Figure

    def prepare(self):
        # this method is executed before starting experiment
        # e.g. initializing Figure

        self._fig, self._ax = plt.subplots(1, 1)

    def update(self, df):
        # this method is executed many times during experiment
        # df is pandas.DataFrame which has experiment data

        self._ax.cla()

        self._ax.plot(df["t"], df["v"])
        self._ax.set_xlabel("Time")
        self._ax.set_ylabel("Voltage")
        self._ax.grid()

if __name__ == "__main__":
    experiment = MyExperiment()
    experiment.plotter = MyPlotter() # Optional
    experiment.start() # calling start() starts infinite loop
