from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
from matplotlib.figure import Figure

from .base import DfPlotter


def df_plotter(plotter_key: str):
    def decorator(func: Callable[[pd.DataFrame, str | Path], None]) -> type[DfPlotter]:
        class Plotter(DfPlotter):
            key = plotter_key

            def plot(self, df: pd.DataFrame, fig: Figure) -> None:
                func(df, fig)

        return Plotter

    return decorator
