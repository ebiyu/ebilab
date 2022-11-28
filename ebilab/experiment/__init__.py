from typing import List

from ._core import Experiment, Plotter
from ._experiment_controller import IExperimentProtocol, ExperimentContext, ExperimentController, IExperimentPlotter

from ._experiment_controller import FileManagerStub
from ._ui_tkinter import ExperimentUITkinter

def launch_experiment(experiments: List[IExperimentProtocol]):
    ui = ExperimentUITkinter()
    file_manager = FileManagerStub()
    app = ExperimentController(experiments=experiments, ui=ui, file_manager=file_manager)
    app.launch()
