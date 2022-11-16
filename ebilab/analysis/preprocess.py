import os
from pathlib import Path
from typing import Callable, Optional, Union

import pandas as pd

from .paths import paths

class DfData:
    _df: pd.DataFrame

    def __init__(self, df):
        self._df = df

    def to(self, file):
        self._df.to_csv(file, index=False)
        return self

    def apply(self, func: Callable[[pd.DataFrame], pd.DataFrame]):
        self._df = func(self._df)
        return self

    def toInput(self, file):
        path = paths.input / file
        if path.exists():
            if os.environ.get("EBILAB_SOURCE") != "WATCH":
                print(f"Already exists: {path.name}")
        else:
            self._df.to_csv(path, index=False)
            print(f"Written to: {path.name}")
        return self

class FileData:
    _filename: Union[str, Path]
    _skip_rows: Optional[int] = None
    def __init__(self, filename: Union[str, Path]):
        self._filename = filename

    def skip(self, skip: int):
        self._skip_rows = skip
        return self

    def csv(self) -> DfData:
        df = pd.read_csv(self._filename, skiprows=self._skip_rows)
        return DfData(df)

def original(filename: str) -> FileData:
    return FileData(paths.original / filename)

