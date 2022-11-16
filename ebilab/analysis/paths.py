from pathlib import Path
from typing import Optional

class DataDirNotFoundDirection(Exception):
    """
    This exception is thrown if directory structure is not correct
    """
    pass

class AnalysisPath:
    _data: Optional[Path] = None

    def _get_path(self):
        _paths = [Path(".").resolve()] + list(Path(".").resolve().parents)
        for path in _paths:
            root = path
            data = root / "data"
            if data.exists():
                break
        else:
            raise Exception("Could not find data directory")
        return data

    @property
    def data(self):
        if self._data is None:
            self._data = self._get_path()
        return self._data

    @property
    def original(self):
        if self._data is None:
            self._data = self._get_path()
        return self._data / "original"

    @property
    def input(self):
        if self._data is None:
            self._data = self._get_path()
        return self._data / "input"

    @property
    def output(self):
        if self._data is None:
            self._data = self._get_path()
        return self._data / "output"

    @property
    def plot(self):
        if self._data is None:
            self._data = self._get_path()
        return self._data / "plot"

paths = AnalysisPath()

