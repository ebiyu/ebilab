from __future__ import annotations

from pathlib import Path
from typing import Callable

# import matplotlib.pyplot as plt  # type: ignore
import pandas as pd  # type: ignore
from matplotlib.figure import Figure  # type: ignore


class DfPlotterMetaClass(type):
    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)
        # register_class(new_cls)
        return new_cls


class DfPlotter(metaclass=DfPlotterMetaClass):
    key: str

    def get_key(self):
        if hasattr(self, "key"):
            return self.key

        raise NotImplementedError("key attribute or get_key method must be implemented in subclass")

    def plot(self, df: pd.DataFrame, fig: Figure) -> None:
        raise NotImplementedError("plot method must be implemented in subclass")


def df_plotter(plotter_key: str):
    def decorator(func: Callable[[pd.DataFrame, str | Path], None]) -> type[DfPlotter]:
        class Plotter(DfPlotter):
            key = plotter_key

            def plot(self, df: pd.DataFrame, fig: Figure) -> None:
                func(df, fig)

        return Plotter

    return decorator
