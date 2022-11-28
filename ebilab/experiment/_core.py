# for backward compatibility
import queue
import inspect
import copy
import sys
from threading import Thread
import time
import datetime
from typing import Optional, List, Callable
import os
import abc

from ._experiment_controller import IExperimentProtocol, IExperimentPlotter, ExperimentContext, ExperimentController
from ._ui_tkinter import ExperimentUITkinter

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd

class Plotter:
    fig: plt.Figure
    def prepare(self):
        raise NotImplementedError("Plotter::prepare() must be implemented")

    def update(self, df: pd.DataFrame):
        raise NotImplementedError("Plotter::update() must be implemented")

class Experiment:
    columns: List[str]
    filename: str

    _plotter: Optional[Plotter] = None

    def _loop(self):
        raise NotImplementedError()

    @property
    def running(self) -> bool:
        self._loop()
        return True

    @property
    def plotter(self) -> Optional[Plotter]:
        return self._plotter

    @plotter.setter
    def plotter(self, plotter: Optional[Plotter]):
        self._plotter = plotter

    def start(self):
        self_outer = self
        if self_outer._plotter is None:
            raise NotImplementedError()
        class ExperimentPlotter(IExperimentPlotter):
            name = "plot"
            _original: Plotter

            def __init__(self) -> None:
                self._original = self_outer._plotter

            def prepare(self):
                self._original.fig = self.fig
                self._original.prepare()

            def update(self, df):
                self._original.update(df)

        class ExperimentProtocol(IExperimentProtocol):
            plotter_classes = [ExperimentPlotter]
            name = self_outer.filename
            columns = self_outer.columns

            def steps(self, ctx: ExperimentContext) -> None: # step of measurement
                def send_row(row, *, capture: Optional[List[str]] = None):
                    row = copy.copy(row)

                    if capture:
                        frame = inspect.currentframe()
                        try:
                            local_vars = frame.f_back.f_locals
                        finally:
                            del frame

                        for var in capture:
                            if var in row:
                                raise ValueError(f"Duplicate key: `{var}` is defined in row and capture.")
                            if var not in local_vars:
                                raise RuntimeError(f"No local variable `{var}` is found.")
                            row[var] = local_vars[var]
                    ctx.send_row(row)
                self_outer.send_row = send_row

                self_outer._loop = ctx.loop

                self_outer.steps()

        ui = ExperimentUITkinter()
        app = ExperimentController(experiments=[ExperimentProtocol], ui=ui)
        app.launch()

    def send_row(self, row, *, capture: Optional[List[str]] = None):
        raise NotImplementedError()

    def steps(self):
        raise NotImplementedError("Experiment::steps() must be implemented")

