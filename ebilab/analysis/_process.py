from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Union, List

import pandas as pd

from ebilab.project import get_current_project
from ._actions import DfAction, DfPlotter, AggregatedDfPlotter

class ProcessingData:
    _df: pd.DataFrame
    _key: str
    _use_cache = True
    def __init__(self, df: pd.DataFrame, key: str, *, save=True):
        self._df = df
        self._key = key
        if save:
            self._save()

    def apply(self, action: DfAction):
        self._key += "__" + action.key
        cache = self._load_csv()
        if cache is None:
            self._df = action.handler(self._df)
            self._save()
            self._use_cache = False
            print(f"Saved: {self._key}.csv")
        else:
            self._df = cache
            if os.environ.get("EBILAB_SOURCE") != "WATCH":
                print(f"Cache available: {self._key}.csv")
        return self

    def query(self, q: str, caption: str):
        def func(df: pd.DataFrame) -> pd.DataFrame:
            return df.query(q)
        return self.apply(DfAction(func, caption))

    def concat(self, other: ProcessingData) -> ProcessingData:
        key1 = re.sub(r"^\((.+)\)$", r"\1", self._key)
        key2 = re.sub(r"^\((.+)\)$", r"\1", other._key)
        return ProcessingData(df=pd.concat([self._df, other._df]), key=f"({key1}+{key2})")

    def nocache(self):
        self._use_cache = False
        return self

    def _load_csv(self):
        if not self._use_cache:
            return None
        dir = get_current_project().path.data_output
        path = dir / (self._key + ".csv")
        if path.exists():
            return pd.read_csv(path)
        return None

    def _save(self):
        dir = get_current_project().path.data_output
        self._df.to_csv(dir / (self._key + ".csv"), index=False)
        return self

    def plot(self, plotter: DfPlotter):

        dir = get_current_project().path.data_plot
        filename = dir / (self._key + "__" + plotter.key + ".png")

        # cache
        if self._use_cache and filename.exists():
            if os.environ.get("EBILAB_SOURCE") != "WATCH":
                print(f"Plot already exists: {filename.name}")
        else:
            plotter.handler(self._df, filename)
            print(f"Saved plot: {filename.name}")

        return self

    def __del__(self):
        # ここでplt.closeすると show() メソッドが作れるかも
        pass

    @classmethod
    def fromCsv(cls, filename: Union[str, Path]):
        path = Path(filename)
        df = pd.read_csv(path)
        return cls(df, path.stem, save=False)

class AggregatedProcessingData:
    _dfs: List[pd.DataFrame]
    _keys: List[str]
    _use_cache = True

    def __init__(self, data: List[ProcessingData]):
        self._dfs = list(map(lambda d:d._df, data))
        self._keys = list(map(lambda d:d._key, data))
        self._use_cache = all(map(lambda d:d._use_cache, data))

    def plot(self, plotter: AggregatedDfPlotter):
        dir = get_current_project().path.data_plot
        filename = dir / (f"[{','.join(self._keys)}]__{plotter.key}.png")

        # cache
        if self._use_cache and filename.exists():
            if os.environ.get("EBILAB_SOURCE") != "WATCH":
                print(f"Plot already exists: {filename.name}")
        else:
            plotter.handler(self._dfs, filename)
            print(f"Saved plot: {filename.name}")

        return self  

    def combine(self, varname: str, values: list):
        dfs_copy = [df.copy() for df in self._dfs]
        for df, val in zip(dfs_copy, values):
            df[varname] = val
        return ProcessingData(
            df=pd.concat(dfs_copy),
            key=f"{varname}[{','.join(self._keys)}]"
        )

    def nocache(self):
        self._use_cache = False
        return self

def aggregate(data: List[ProcessingData]) -> AggregatedProcessingData:
    return AggregatedProcessingData(data)

def input(filename: str) -> ProcessingData:
    return ProcessingData.fromCsv(get_current_project().path.data_input / filename)

def output(filename: str) -> ProcessingData:
    return ProcessingData.fromCsv(get_current_project().path.data_output / filename)

def from_df(df: pd.DataFrame, key: str) -> ProcessingData:
    return ProcessingData(df, key)
