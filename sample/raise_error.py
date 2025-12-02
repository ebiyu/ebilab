# sample of GUI app - Raise Error Recipe

from ebilab.api import BaseExperiment
from ebilab.gui.controller import launch_gui


class RaiseErrorExperiment(BaseExperiment):
    """
    Raise Error Experiment

    This experiment intentionally raises a ValueError to test error handling.
    """

    columns = []
    name = "raise-error"

    async def setup(self):
        self.logger.info("Setting up raise error experiment...")

    async def steps(self):
        self.logger.info("About to raise an error...")
        raise ValueError("Test error")

    async def cleanup(self):
        self.logger.info("Raise error experiment finished.")


if __name__ == "__main__":
    # This is a sample code to run the experiment
    # You can run this file directly to see the experiment in action
    launch_gui([RaiseErrorExperiment])
