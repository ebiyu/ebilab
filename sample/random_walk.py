# sample of GUI app
import asyncio
import random

from ebilab.api import BaseExperiment, BasePlotter, FloatField, SelectField
from ebilab.gui.controller import launch_gui


# class to decide steps of experiment
class RandomWalkExperiment(BaseExperiment):
    """
    Random Walk

    This is example experiment.
    The interval is 0.2 sec.
    """

    columns = ["v", "v2"]  # please specify columns to write csv file
    name = "random-walk"  # filename is suffixed by datetime

    initial = FloatField(default=2.0)
    step = SelectField(choices=[1, 2, 4], default_index=1)

    async def setup(self):
        self.v = self.initial
        self.logger.info(f"Random walk experiment started with initial value {self.v}.")

    async def steps(self):
        self.logger.info("Starting random walk experiment.")
        while True:
            # you can use self.logger to log messages
            self.logger.debug(f"log: {self.v}")

            # random walk logic
            step_value = self.step if random.random() < 0.5 else -self.step
            self.v += step_value

            # The value you yield will be sent to GUI and saved to CSV file
            yield {"v": self.v, "v2": self.v * 2}

            # use asyncio.sleep instead of time.sleep
            await asyncio.sleep(0.2)

    async def cleanup(self):
        self.logger.info("Random walk experiment finished.")


#  class to decide how to plot during experiment
@RandomWalkExperiment.register_plotter
class TransientPlotter(BasePlotter):
    name = "transient"

    def setup(self):
        # this method is executed before starting experiment
        # e.g. adding Axes to Figure
        # figure is stored in `self.fig`
        if self.fig:
            self._ax = self.fig.add_subplot(111)

    def update(self, df):
        # this method is executed many times during experiment
        # df is pandas.DataFrame which has experiment data
        if hasattr(self, "_ax") and not df.empty:
            self._ax.clear()

            self._ax.plot(df["t"], df["v"])
            self._ax.set_xlabel("Time")
            self._ax.set_ylabel("Voltage")
            self._ax.grid(True)
            self._ax.text(0.05, 0.95, f"step={self.experiment.step}", transform=self._ax.transAxes, verticalalignment='top')


#  class to decide how to plot during experiment
@RandomWalkExperiment.register_plotter
class HistgramPlotter(BasePlotter):
    name = "histgram"
    bins = FloatField(default=10.0)

    def setup(self):
        # this method is executed before starting experiment
        # e.g. adding Axes to Figure
        # figure is stored in `self.fig`
        if self.fig:
            self._ax = self.fig.add_subplot(111)

    def update(self, df):
        # this method is executed many times during experiment
        # df is pandas.DataFrame which has experiment data
        if hasattr(self, "_ax") and not df.empty and "v" in df.columns:
            self._ax.clear()

            self._ax.hist(df["v"], bins=int(self.bins))
            self._ax.set_xlabel("Value")
            self._ax.set_ylabel("Count")
            
            # 実験インスタンスにアクセスしてパラメータを表示
            if self.experiment:
                title = f"Histogram (step={self.experiment.step}, initial={self.experiment.initial})"
                self._ax.set_title(title)
                # ログに出力してテスト
                self.experiment.logger.info(f"Plotter accessed experiment parameters: step={self.experiment.step}")
            
            self._ax.grid(True)


if __name__ == "__main__":
    # This is a sample code to run the experiment
    # You can run this file directly to see the experiment in action
    launch_gui([RandomWalkExperiment])
