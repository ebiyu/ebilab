# sample of asyncio.sleep - Context Sleep Recipe

import asyncio

from ebilab.api import BaseExperiment, FloatField
from ebilab.gui.controller import launch_gui


class ContextSleepExperiment(BaseExperiment):
    """
    Context Sleep Experiment

    This experiment sleeps for a specified amount of time.
    Uses asyncio.sleep to make the STOP button work properly.
    """

    columns = []
    name = "ctx-sleep"

    time = FloatField(default=10.0, min=0.1, max=300.0)

    async def setup(self):
        self.logger.info(f"Setting up context sleep experiment for {self.time} seconds...")

    async def steps(self):
        self.logger.info(f"Sleeping for {self.time} seconds...")
        # you have to use asyncio.sleep instead of time.sleep in order to make STOP button work
        await asyncio.sleep(self.time)
        self.logger.info("Sleep completed.")

    async def cleanup(self):
        self.logger.info("Context sleep experiment finished.")


if __name__ == "__main__":
    # This is a sample code to run the experiment
    # You can run this file directly to see the experiment in action
    launch_gui([ContextSleepExperiment])
