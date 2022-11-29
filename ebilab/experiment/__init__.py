from typing import List, Type

from ._experiment_controller import IExperimentProtocol, ExperimentContext, ExperimentController, IExperimentPlotter

def launch_experiment(experiments: List[Type[IExperimentProtocol]]):
    from ._ui_tkinter import ExperimentUITkinter
    ui = ExperimentUITkinter()
    app = ExperimentController(experiments=experiments, ui=ui)
    app.launch()
