from __future__ import annotations

import importlib
import sys
import dataclasses
from pathlib import Path
from typing import Any, Generator

import pandas as pd

from .plotter import DfPlotter


@dataclasses.dataclass
class ProcessStep:
    process_step: str
    kwargs: dict[str, Any]

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError()
        # TODO: Implement apply method


@dataclasses.dataclass
class PlotterStep:
    process_step: str
    kwargs: dict[str, Any]

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError()
        # TODO: Implement apply method


@dataclasses.dataclass
class InputManifest:
    name: str
    original: str  # posix path relative to "original" directory
    process_steps: list[ProcessStep] | None = None


@dataclasses.dataclass
class ProcessManifest:
    input: str
    process_steps: list[ProcessStep] = dataclasses.field(default_factory=list)
    plotter: PlotterStep | None = None


def to_list(func):
    def wrapper(*args, **kwargs):
        return list(func(*args, **kwargs))

    return wrapper


def find_subclasses(module: Any, cls: type) -> Generator[tuple[str, type], None, None]:
    for name, item in module.__dict__.items():
        if isinstance(item, type) and issubclass(item, cls):
            yield name, item


class SubProject:
    modules: dict[str, Any]
    inputs: list[InputManifest]  # TODO: sync with file
    outputs: list[ProcessManifest]  # TODO: sync with file

    current_recipe: ProcessManifest | None  # on memory recipe

    def __init__(self, path: Path):
        self.path = path
        self.modules = self._import_scripts()
        self.inputs = []
        self.outputs = []
        self.current_recipe = None

    def __repr__(self) -> str:
        return f'<ebilib.subproject.SubProject("{self.path}")>'

    @property
    def src_path(self) -> Path:
        return self.path / "src"

    def _find_python_scripts(self) -> Generator[Path, None, None]:
        """
        Yields python scripts in the ./src directory recursively
        """
        yield from self.src_path.rglob("*.py")

    def _import_scripts(self, reload: bool = False) -> dict[str, Any]:
        """
        Import all python scripts in the ./src directory
        """
        ret: dict[str, Any] = {}

        project_path = self.path.resolve().parent
        old_path = sys.path
        sys.path.append(project_path.as_posix())
        for script in self._find_python_scripts():
            module_name = (
                script.relative_to(project_path).with_suffix("").as_posix().replace("/", ".")
            )
            module = importlib.import_module(module_name)
            if reload:
                importlib.reload(module)
            ret[module_name] = module
        sys.path = old_path
        return ret

    def reload(self):
        """
        Reload all python scripts in the ./src directory
        """
        self.modules = self._import_scripts(reload=True)

    @property
    def df_plotters(self) -> dict[str, type[DfPlotter]]:
        """
        Returns a dictionary of all DfPlotter subclasses in the subproject
        """
        res: dict[str, type[DfPlotter]] = {}
        for module_name, module in self.modules.items():
            for name, plotter in find_subclasses(module, DfPlotter):
                res[module_name + "." + name] = plotter
        return res
