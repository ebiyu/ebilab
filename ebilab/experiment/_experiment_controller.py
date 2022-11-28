import datetime
import sys
import abc
import copy
import time
import queue
from typing import List, Optional, Type, Literal
import weakref
from threading import Thread

# dependencies of ExperimentController
class ExperimentContextDelegate(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def experiment_ctx_delegate_send_row(self, row=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def experiment_ctx_delegate_get_t(self) -> float:
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

    def loop(self) -> None:
        self._delegate.experiment_ctx_delegate_loop()

class IExperimentPlotter(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def prepare(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self, df):
        raise NotImplementedError()

class IExperimentProtocol(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def plotter_classes(self) -> List[Type[IExperimentPlotter]]:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def columns(self) -> List[str]:
        raise NotImplementedError()

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
    def update_state(self, state: Literal["running", "stopping", "stopped"]):
        raise NotImplementedError()

    @abc.abstractmethod
    def reset_data(self):
        raise NotImplementedError()

class IFileManager(metaclass=abc.ABCMeta):
    @property
    def data_queue(self) -> queue.Queue:
        raise NotImplementedError()

class ExperimentController(ExperimentContextDelegate, ExperimentUIDelegate):
    _experiments: List[Type[IExperimentProtocol]]
    _ui: IExperimentUI
    _file_manager: IFileManager
    _ctx: ExperimentContext
    _running = False

    def __init__(self, *, experiments=List[Type[IExperimentProtocol]], ui: IExperimentUI, file_manager: IFileManager):
        self._experiments = experiments

        self._ui = ui
        self._ui.delegate = self
        self._ui.experiments = experiments

        self._file_manager = file_manager

    def launch(self):
        self._ui.launch()

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

        self._ctx = ExperimentContext(delegate=self)

        def run():
            self._running_experiment.steps(self._ctx)
            time.sleep(1)
            self._completed = True

        self._started_time = time.perf_counter()
        self._running = True
        self._experiment_thread = Thread(target=run)
        self._experiment_thread.daemon = True
        self._experiment_thread.start()

    def _stop(self):
        self._ui.update_state("stopping")
        self._running = False
        self._experiment_thread.join()
        self._ui.update_state("stopped")

    def _get_t(self) -> float:
        return time.perf_counter() - self._started_time

    # ExperimentContextDelegate
    def experiment_ctx_delegate_send_row(self, row=None):
        row = copy.copy(row)
        row["t"] = self._get_t()
        row["time"] = datetime.datetime.now()

        self._ui.data_queue.put(row)
        self._file_manager.data_queue.put(row)

    def experiment_ctx_delegate_get_t(self) -> float:
        return self._get_t()

    def experiment_ctx_delegate_loop(self) -> None:
        if not self._running:
            sys.exit()

    # ExperimentUIDelegate
    def handle_ui_start(self, experiment_index: int, plotter_index: int):
        self._run(experiment_index, plotter_index)

    def handle_ui_stop(self):
        self._stop()

class FileManagerStub(IFileManager):
    _data_queue: queue.Queue
    def __init__(self) -> None:
        super().__init__()
        self._data_queue = queue.Queue()

    @property
    def data_queue(self) -> queue.Queue:
        return self._data_queue
