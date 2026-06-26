# sample of `plotters = [...]` declaration with SimpleXYPlotter
import asyncio
import random

from ebilab.api import BaseExperiment, FloatField, SimpleXYPlotter
from ebilab.gui.controller import launch_gui


class RandomWalkExperiment(BaseExperiment):
    """Random walk demo using SimpleXYPlotter instances."""

    columns = ["v", "v2"]
    name = "simple-plot-demo"

    initial = FloatField(default=2.0)

    plotters = [
        SimpleXYPlotter("t", "v"),
        SimpleXYPlotter("t", ["v", "v2"], name="v and v2"),
    ]

    async def setup(self):
        self.v = self.initial

    async def steps(self):
        while True:
            self.v += random.choice([-1, 1])
            yield {"v": self.v, "v2": self.v * 2}
            await asyncio.sleep(0.2)


if __name__ == "__main__":
    launch_gui([RandomWalkExperiment])
