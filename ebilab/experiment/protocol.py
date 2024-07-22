"""
Base classes

Users will define protocol by overriding classes here.
"""
from __future__ import annotations

import abc
import dataclasses
import time
from pathlib import Path

import matplotlib.pyplot as plt  # type: ignore

from .options import OptionField


# dependencies of ExperimentController
class ExperimentContextDelegate(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def experiment_ctx_delegate_send_row(self, row):
        raise NotImplementedError()

    @abc.abstractmethod
    def experiment_ctx_delegate_send_log(self, log: str):
        raise NotImplementedError()

    @abc.abstractmethod
    def experiment_ctx_delegate_get_t(self) -> float:
        raise NotImplementedError()

    @abc.abstractmethod
    def experiment_ctx_delegate_get_options(self) -> dict:
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

    def log(self, log: str):
        self._delegate.experiment_ctx_delegate_send_log(log)

    @property
    def t(self) -> float:
        return self._delegate.experiment_ctx_delegate_get_t()

    @property
    def options(self) -> dict:
        return self._delegate.experiment_ctx_delegate_get_options()

    def loop(self) -> None:
        self._delegate.experiment_ctx_delegate_loop()

    def sleep(self, sleep_time: float) -> None:
        """
        Cancelable sleep
        You should use ctx.sleep instead of time.sleep

        Args:
            sleep_time (float): Time to sleep
        """
        target = time.time() + sleep_time
        while target - time.time() > 1.0:
            time.sleep(1)
            self.loop()

        time.sleep(target - time.time())


@dataclasses.dataclass
class PlotterContext:
    plotter_options: dict
    protocol_options: dict


class ExperimentPlotter(metaclass=abc.ABCMeta):
    fig: plt.Figure
    name: str

    options: dict[str, OptionField] | None = None

    @abc.abstractmethod
    def prepare(self, ctx: PlotterContext):
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self, df, ctx: PlotterContext):
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True)
class ExperimentProtocolSourceInfo:
    filepath: Path
    module_name: str


class ExperimentProtocol(metaclass=abc.ABCMeta):
    name: str
    columns: list[str]
    plotter_classes: list[type[ExperimentPlotter]] | None = None
    source_info: ExperimentProtocolSourceInfo | None = None

    options: dict[str, OptionField] | None = None

    @classmethod
    def get_summary(cls):
        if cls.__doc__ is None:
            return cls.name
        return cls.__doc__.strip().splitlines()[0].strip()

    @classmethod
    def get_description(cls):
        if cls.__doc__ is None:
            return "There's no description"
        lines = cls.__doc__.strip().splitlines()[1:]
        lines = map(lambda x: x.strip(), lines)
        return "\n".join(lines).strip()

    @abc.abstractmethod
    def steps(self, ctx: ExperimentContext) -> None:
        raise NotImplementedError()

    @classmethod
    def register_plotter(cls, plotter):
        if cls.plotter_classes is None:
            cls.plotter_classes = []
        cls.plotter_classes.append(plotter)


@dataclasses.dataclass(frozen=True)
class ExperimentProtocolGroup:
    name: str
    protocols: list[type[ExperimentProtocol]]
