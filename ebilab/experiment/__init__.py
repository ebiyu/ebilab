from typing import List, Type

from .protocol import (
    ExperimentProtocol,
    ExperimentContext,
    ExperimentPlotter,
    PlotterContext,
    ExperimentProtocolGroup,
)
from ._experiment_controller import ExperimentController
from ._experiment_manager import ExperimentManager


def launch_experiment(experiments: List[Type[ExperimentProtocol]]):
    from ._ui_tkinter import ExperimentUITkinter

    experiment_manager = ExperimentManager.from_experiments(experiments)
    ui = ExperimentUITkinter(experiment_manager)
    ui.launch()


__all__ = [
    "ExperimentProtocol",
    "ExperimentContext",
    "ExperimentController",
    "ExperimentPlotter",
    "PlotterContext",
    "ExperimentProtocolGroup",
]
