import datetime
import numbers
import os
import sys
import csv
import abc
import socket
import copy
import time
import queue
from pathlib import Path
from typing import List, Optional, Type, Dict
import weakref
from threading import Thread

import matplotlib.pyplot as plt

from .options import OptionField
from ..project import get_current_project

# dependencies of ExperimentController
class ExperimentContextDelegate(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def experiment_ctx_delegate_send_row(self, row):
        raise NotImplementedError()

    @abc.abstractmethod
    def experiment_ctx_delegate_get_t(self) -> float:
        raise NotImplementedError()

    @abc.abstractmethod
    def experiment_ctx_delegate_get_options(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def experiment_ctx_delegate_loop(self) -> None:
        raise NotImplementedError()

class ExperimentContext:
    _delegate: ExperimentContextDelegate
    def __init__(self, delegate: ExperimentContextDelegate):
        self._delegate = delegate

    def send_row(self, row: dict):
        self._delegate.experiment_ctx_delegate_send_row(row)

    @property
    def t(self) -> float:
        return self._delegate.experiment_ctx_delegate_get_t()

    @property
    def options(self) -> dict:
        return self._delegate.experiment_ctx_delegate_get_options()

    def loop(self) -> None:
        self._delegate.experiment_ctx_delegate_loop()

class IExperimentPlotter(metaclass=abc.ABCMeta):
    fig: plt.Figure
    name: str

    options: Optional[Dict[str, OptionField]]

    @abc.abstractmethod
    def prepare(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self, df):
        raise NotImplementedError()

class IExperimentProtocol(metaclass=abc.ABCMeta):
    name: str
    columns: List[str]
    plotter_classes: List[Type[IExperimentPlotter]]

    @abc.abstractmethod
    def steps(self, ctx: ExperimentContext) -> None:
        raise NotImplementedError()

class ExperimentUIDelegate(metaclass=abc.ABCMeta):
    # UI -> Coreの操作
    @abc.abstractmethod
    def handle_ui_start(self, experiment_index: int, plotter_index: int):
        raise NotImplementedError

    @abc.abstractmethod
    def handle_ui_stop(self):
        raise NotImplementedError

class IExperimentUI(metaclass=abc.ABCMeta):
    __delegate_ref = None

    @property
    def delegate(self) -> Optional[ExperimentUIDelegate]:
        if self.__delegate_ref is None:
            return None
        return self.__delegate_ref()

    @delegate.setter
    def delegate(self, delegate: ExperimentUIDelegate):
        self.__delegate_ref = weakref.ref(delegate)

    @property
    @abc.abstractmethod
    def data_queue(self) -> queue.Queue:
        raise NotImplementedError()

    experiments: List[Type[IExperimentProtocol]]

    @abc.abstractmethod
    def launch(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def set_plotter(self, plotter: Optional[IExperimentPlotter]):
        raise NotImplementedError()

    @abc.abstractmethod
    def update_state(self, state: str):
        raise NotImplementedError()

    @abc.abstractmethod
    def reset_data(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_options(self) -> dict:
        raise NotImplementedError()

    @property
    def experiment_label(self) -> str:
        return NotImplementedError()

class ExperimentController(ExperimentContextDelegate, ExperimentUIDelegate):
    _experiments: List[Type[IExperimentProtocol]]
    _ui: IExperimentUI
    _ctx: ExperimentContext
    _running = False
    _file = None

    _experiment_thread = None

    def __init__(self, *, experiments: List[Type[IExperimentProtocol]], ui: IExperimentUI):
        self._experiments = experiments

        self._ui = ui
        self._ui.delegate = self
        self._ui.experiments = experiments

    def launch(self):
        self._ui.launch()

    def _get_comment_line(self, experiment: IExperimentProtocol, options: dict) -> str:
        """
        Returns: 
            str: includes trailing NL
        """
        exp_name = experiment.name
        date = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        pc_name = socket.gethostname()
        options_str = ", ".join([f"{k}: {v}" for k, v in options.items()]) if options else ""

        comment_str = ""
        comment_str += f"# {exp_name} experiment: Ran at {date} in {pc_name}\n"
        comment_str += f"# {options_str}\n"
        comment_str += f"#\n"
        return comment_str

    def _run(self, experiment_index: int, plotter_index: int):
        self._ui.update_state("running")

        self._running_experiment_idx = experiment_index
        self._running_plotter_idx = plotter_index
        self._running_experiment_class = self._experiments[experiment_index]
        self._running_plotter_class = self._running_experiment_class.plotter_classes[plotter_index]
        self._running_experiment = self._running_experiment_class()
        self._running_plotter = self._running_plotter_class()
        self._ui.set_plotter(self._running_plotter)

        self._ui.reset_data()

        self._options = self._ui.get_options()

        self._ctx = ExperimentContext(delegate=self)

        # file
        try:
            data_dir = get_current_project().path.data_original
        except:
            data_dir = Path(".") / "data"
        dir = data_dir / datetime.datetime.now().strftime("%y%m%d")
        os.makedirs(dir, exist_ok=True)
        label = self._ui.experiment_label or self._running_experiment.name
        filename = label + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv"
        self._filename = dir / filename
        self._file = open(self._filename, "w", newline="")
        self._csv_writer = csv.writer(self._file, quoting=csv.QUOTE_NONNUMERIC)

        comment_lines = self._get_comment_line(self._running_experiment, self._options)
        self._file.write(comment_lines)

        header = ["t", "time"] + self._running_experiment.columns
        self._csv_writer.writerow(header)

        def run():
            self._running_experiment.steps(self._ctx)
            time.sleep(1)
            self._running = False
            self._ui.update_state("stopped")

        self._started_time = time.perf_counter()
        self._running = True
        self._experiment_thread = Thread(target=run)
        self._experiment_thread.daemon = True
        self._experiment_thread.start()

    def _stop(self):

        self._ui.update_state("stopping")
        self._running = False
        if self._experiment_thread is not None:
            self._experiment_thread.join()
        self._ui.update_state("stopped")

        if self._file is not None:
            self._file.close()

    def _get_t(self) -> float:
        return time.perf_counter() - self._started_time

    # ExperimentContextDelegate
    def experiment_ctx_delegate_send_row(self, row):
        row = copy.copy(row)
        row["t"] = self._get_t()
        row["time"] = datetime.datetime.now()

        self._ui.data_queue.put(row)

        # write to file
        cols = ["t", "time"] + self._running_experiment.columns
        row_list = [row.get(col) for col in cols]
        self._csv_writer.writerow(row_list)

    def experiment_ctx_delegate_get_t(self) -> float:
        return self._get_t()

    def experiment_ctx_delegate_get_options(self) -> None:
        return self._options

    def experiment_ctx_delegate_loop(self) -> None:
        if not self._running:
            sys.exit()

    # ExperimentUIDelegate
    def handle_ui_start(self, experiment_index: int, plotter_index: int):
        self._run(experiment_index, plotter_index)

    def handle_ui_stop(self):
        self._stop()

    def __del__(self):
        if self._file is not None:
            self._file.close()

