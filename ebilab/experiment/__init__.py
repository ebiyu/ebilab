from __future__ import annotations

from ._experiment_manager import ExperimentManager
from .protocol import (
    ExperimentContext,
    ExperimentPlotter,
    ExperimentProtocol,
    ExperimentProtocolGroup,
    PlotterContext,
)


def launch_experiment(experiments: list[type[ExperimentProtocol]]) -> None:
    from ._ui_tkinter import ExperimentUITkinter

    experiment_manager = ExperimentManager.from_experiments(experiments)
    ui = ExperimentUITkinter(experiment_manager)
    ui.launch()


__all__ = [
    "ExperimentProtocol",
    "ExperimentContext",
    "ExperimentPlotter",
    "PlotterContext",
    "ExperimentProtocolGroup",
    "launch_experiment",
]
