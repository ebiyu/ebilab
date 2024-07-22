# sample of GUI app
import time
import random

from ebilab.experiment import (
    ExperimentProtocol,
    ExperimentPlotter,
    ExperimentContext,
    PlotterContext,
    launch_experiment,
)
from ebilab.experiment.options import FloatField, SelectField


class NothingExperiment(ExperimentProtocol):
    columns = []
    name = "do-noting"
    plotter_classes = []

    # available in GUI
    options = {}

    def steps(self, ctx: ExperimentContext) -> None:  # step of measurement
        pass
