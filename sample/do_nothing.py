# sample of GUI app - Do Nothing Recipe

from ebilab.api import BaseExperiment
from ebilab.gui.controller import launch_gui


class DoNothingExperiment(BaseExperiment):
    """
    Do Nothing Experiment

    This experiment does nothing and immediately finishes.
    """

    columns = []
    name = "do-nothing"

    async def setup(self):
        self.logger.info("Setting up do nothing experiment...")

    async def steps(self):
        self.logger.info("Do nothing experiment - doing nothing and finishing.")
        return
        yield  # unreachable, but needed for generator

    async def cleanup(self):
        self.logger.info("Do nothing experiment finished.")


if __name__ == "__main__":
    # This is a sample code to run the experiment
    # You can run this file directly to see the experiment in action
    launch_gui([DoNothingExperiment])
