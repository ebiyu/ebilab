from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Union, Callable, List
from dataclasses import dataclass

import pandas as pd

from .paths import paths

@dataclass
class DfAction:
    handler: Callable[[pd.DataFrame], pd.DataFrame]
    key: str

    def get_key(self):
        return self.key

@dataclass
class DfPlotter:
    handler: Callable[[pd.DataFrame, Union[str, Path]], None]
    key: str

    def get_key(self):
        return self.key

@dataclass
class AggregatedDfPlotter:
    handler: Callable[[List[pd.DataFrame], Union[str, Path]], None]
    key: str

    def get_key(self):
        return self.key


def df_action(key: str):
    def decorator(func: Callable[[pd.DataFrame], pd.DataFrame]):
        return DfAction(handler=func, key=key)
    return decorator

def df_plotter(key: str):
    def decorator(func: Callable[[pd.DataFrame, Union[str, Path]], None]):
        return DfPlotter(handler=func, key=key)
    return decorator

def agg_df_plotter(key: str):
    def decorator(func: Callable[[List[pd.DataFrame], Union[str, Path]], None]):
        return AggregatedDfPlotter(handler=func, key=key)
    return decorator


class ProcessingData:
    _df: pd.DataFrame
    _key: str
    _use_cache = True
    def __init__(self, df: pd.DataFrame, key: str):
        self._df = df
        self._key = key

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
        path = paths.output / (self._key + ".csv")
        if path.exists():
            return pd.read_csv(path)
        return None

    def _check_png(self) -> bool:
        path = paths.output / (self._key + ".png")
        return self._use_cache and path.exists()

    def _save(self):
        self._df.to_csv(paths.output / (self._key + ".csv"), index=False)
        return self

    def plot(self, plotter: DfPlotter):
        filename = paths.plot / (self._key + "__" + plotter.key + ".png")

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
        return cls(df, path.stem)

class AggregatedProcessingData:
    _dfs: List[pd.DataFrame]
    _keys: List[str]
    _use_cache = True

    def __init__(self, data: List[ProcessingData]):
        self._dfs = list(map(lambda d:d._df, data))
        self._keys = list(map(lambda d:d._key, data))
        self._use_cache = all(map(lambda d:d._use_cache, data))

    def plot(self, plotter: AggregatedDfPlotter):
        filename = paths.plot / ("[" + ",".join(self._keys) + "]__" + plotter.key + ".png")

        # cache
        if self._use_cache and filename.exists():
            if os.environ.get("EBILAB_SOURCE") != "WATCH":
                print(f"Plot already exists: {filename.name}")
        else:
            plotter.handler(self._dfs, filename)
            print(f"Saved plot: {filename.name}")

        return self  

    def nocache(self):
        self._use_cache = False
        return self

def aggregate(data: List[ProcessingData]):
    return AggregatedProcessingData(data)

def input(filename: str):
    return ProcessingData.fromCsv(paths.input / filename)

def output(filename: str):
    return ProcessingData.fromCsv(paths.output / filename)

def fromDf(df: pd.DataFrame, key: str):
    return ProcessingData(df, key)
