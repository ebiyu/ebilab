from __future__ import annotations

from io import TextIOWrapper
from typing import Any

import pandas as pd  # type: ignore
from matplotlib.figure import Figure  # type: ignore

from .options import OptionField


class ClassWithOption:
    def __init__(self, kwargs):
        self.kwargs = kwargs

        # inject kwargs
        options = self.get_options()
        for k in options.keys():
            if k in kwargs:
                setattr(self, k, kwargs[k])
            else:
                raise ValueError(f"Missing required option: {k}")

    @classmethod
    def get_options(self) -> dict[str, OptionField]:
        if hasattr(self, "options"):
            return self.options

        # discover class/instance attributes
        options = {}
        for attr in dir(self):
            class_ = getattr(self, attr).__class__
            if issubclass(class_, OptionField):
                options[attr] = getattr(self, attr)

        return options

    def get_caption(self) -> str:
        options = self.get_options()
        if not options:
            return self.__class__.__name__
        return (
            self.__class__.__name__
            + "("
            + ", ".join([f"{k}={repr(self.kwargs[k])}" for k, v in options.items()])
            + ")"
        )

    @classmethod
    def get_default_options(cls) -> dict[str, Any]:
        default_options = {}
        fields = cls.get_options()
        for k, field in fields.items():
            default_options[k] = field.get_default()
        return default_options


class DfPlotter(ClassWithOption):
    def plot(self, df: pd.DataFrame, fig: Figure) -> None:
        raise NotImplementedError("plot method must be implemented in subclass")


class FileProcess:
    def process(self, fin: TextIOWrapper, fout: TextIOWrapper) -> None:
        raise NotImplementedError("process method must be implemented in subclass")


class DfProcess(ClassWithOption):
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("process method must be implemented in subclass")
