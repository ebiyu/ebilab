from __future__ import annotations

from pathlib import Path
from typing import Union, Callable, List
from dataclasses import dataclass

import pandas as pd

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


