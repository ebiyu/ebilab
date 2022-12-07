from typing import List, Type

from ._experiment_controller import ExperimentProtocol, ExperimentContext, ExperimentController, ExperimentPlotter, PlotterContext

def launch_experiment(experiments: List[Type[ExperimentProtocol]]):
    from ._ui_tkinter import ExperimentUITkinter
    ui = ExperimentUITkinter()
    app = ExperimentController(experiments=experiments, ui=ui)
    app.launch()
