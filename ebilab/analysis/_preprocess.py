from __future__ import annotations

import os
import tempfile
from io import TextIOWrapper
from pathlib import Path
from typing import Callable, Optional, Union, Dict

import pandas as pd

from ebilab.project import get_current_project

class PreprocessDfData:
    _df: pd.DataFrame

    def __init__(self, df):
        self._df = df

    def apply(self, func: Callable[[pd.DataFrame], pd.DataFrame]):
        self._df = func(self._df)
        return self
    
    def rename_cols(self, mapper: Dict[str, str]):
        self._df = self._df.rename(columns=mapper)
        return self

    def toInput(self, file):
        path = get_current_project().path.data_input / file
        if path.exists():
            if os.environ.get("EBILAB_SOURCE") != "WATCH":
                print(f"Already exists: {path.name}")
        else:
            self._df.to_csv(path, index=False)
            print(f"Written to: {path.name}")
        return self

class PreprocessFileData:
    _filename: Union[str, Path]
    _tmp_filename: Optional[Union[str, Path]] = None
    _skip_rows: Optional[int] = None
    def __init__(self, filename: Union[str, Path]):
        self._filename = filename

    def skip(self, skip: int):
        self._skip_rows = skip
        return self

    def apply(self, func: Callable[[TextIOWrapper, TextIOWrapper], PreprocessFileData]):
        with open(self._filename) as fin:
            fd, tmpfile = tempfile.mkstemp()
            os.close(fd)
            with open(tmpfile, 'w') as fout:
                func(fin, fout)
            self._tmp_filename = tmpfile
        return self
    
    def _remove_header_comment(self):
        def func(fin, fout):
            for line in fin:
                if line[0] != "#":
                    fout.write(line)
                    break
            for line in fin:
                fout.write(line)
        self.apply(func)

    def csv(self) -> PreprocessDfData:
        self._remove_header_comment()
        filename = self._tmp_filename or self._filename
        df = pd.read_csv(filename, skiprows=self._skip_rows)
        return PreprocessDfData(df)

    def __del__(self):
        if self._tmp_filename is not None:
            os.remove(self._tmp_filename)


def original(filename: str) -> PreprocessFileData:
    path = get_current_project().path.data_original / filename
    return PreprocessFileData(path)

