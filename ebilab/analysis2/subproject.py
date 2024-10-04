from __future__ import annotations

import importlib
import os
import sys
import tempfile
from logging import getLogger
from pathlib import Path
from typing import Any, Generator, TypeVar

import chardet
import pandas as pd
import yaml
from matplotlib.figure import Figure

from .base import DfPlotter, DfProcess, FileProcess
from .manifest import DfProcessManifest, InputManifest, Manifest, ManifestParseError

logger = getLogger(__name__)


def to_list(func):
    def wrapper(*args, **kwargs):
        return list(func(*args, **kwargs))

    return wrapper


def find_subclasses(module: Any, cls: type) -> Generator[tuple[str, type], None, None]:
    for name, item in module.__dict__.items():
        if isinstance(item, type) and issubclass(item, cls) and not item == cls:
            yield name, item


T = TypeVar("T")


def get_encoding_type(file):
    with open(file, "rb") as f:
        rawdata = f.read()
    return chardet.detect(rawdata)["encoding"]


class SubProject:
    modules: dict[str, Any]

    manifest: Manifest

    current_recipe: DfProcessManifest | None  # on memory recipe

    def __init__(self, path: Path):
        self.path = path
        self.modules = self._import_scripts()
        self.manifest = Manifest(version="0.1", inputs={}, outputs={})
        self.current_recipe = None

        self.load_manifest()

    def __repr__(self) -> str:
        return f'<ebilib.subproject.SubProject("{self.path}")>'

    def load_manifest(self) -> None:
        """
        Load manifest file
        """

        yaml_path = self.path / "ebilab.sub.yml"
        with open(yaml_path) as fin:
            yaml_data = yaml.safe_load(fin)

        manifest = Manifest.from_dict(yaml_data)
        if manifest.version != "0.1":
            raise ManifestParseError(f"Unsupported version: {manifest.version}")

        self.manifest = manifest

    def save_manifest(self) -> None:
        """
        Save subproject to file
        """

        yaml_data = self.manifest.as_dict()

        yaml_path = self.path / "ebilab.sub.yml"
        with open(yaml_path, "w") as fout:
            yaml.safe_dump(yaml_data, fout, sort_keys=False)

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

    @property
    def df_processes(self) -> dict[str, type[DfProcess]]:
        """
        Returns a dictionary of all DfPlotter subclasses in the subproject
        """
        res: dict[str, type[DfProcess]] = {}
        for module_name, module in self.modules.items():
            for name, plotter in find_subclasses(module, DfProcess):
                res[module_name + "." + name] = plotter
        return res

    def get_class_from_name(self, name: str, base_class: type[T]) -> type[T]:
        """
        Get class from name
        """
        if base_class == DfPlotter:
            ret: type | None = self.df_plotters.get(name)
            if ret is not None:
                return ret
        # TODO: look for df process

        # import module and find class
        module_name, class_name = name.rsplit(".", 1)
        logger.debug(f"Importing module: {module_name}")
        module = importlib.import_module(module_name)
        for n, cls in module.__dict__.items():
            if n == class_name and issubclass(cls, base_class):
                return cls

        raise ValueError(f"Class not found: {name}")

    def get_df_from_input_manifest(self, input_manifest: InputManifest) -> pd.DataFrame:
        """
        Get pandas DataFrame from input manifest
        """
        logger.info("Processing input manifest")

        path = self.path.parent / "data" / "original" / input_manifest.original
        logger.info(f"Target file: {path}")

        # Process file
        for process in input_manifest.file_process_steps:
            process_class = self.get_class_from_name(process.file_process, FileProcess)
            process_instance = process_class()  # TODO: kwargs

            codec = get_encoding_type(str(path))
            logger.debug(f"Detected encoding: {codec}")

            with open(str(path), encoding=codec) as fin:
                fd, tmpfile = tempfile.mkstemp()
                os.close(fd)
                with open(tmpfile, "w") as fout:
                    process_instance.process(fin, fout)

                path = Path(tmpfile)
            logger.info(f"Applied file process: {process.file_process}, saved to {path}")

        # read_csv
        logger.info(f"Reading file: {path}")
        codec = get_encoding_type(str(path))
        logger.debug(f"Detected encoding: {codec}")

        df = pd.read_csv(path, encoding=codec)
        logger.debug(df.shape)
        logger.debug(df.columns)

        # TODO: process_steps

        return df

    def get_input_manifest(self, name: str) -> InputManifest:
        """
        Get input manifest from name
        """
        manifest = self.manifest.inputs.get(name)
        if manifest is None:
            raise ValueError(f"Input manifest not found: {name}")
        return manifest

    def get_df_from_process_manifest(self, process_manifest: DfProcessManifest) -> pd.DataFrame:
        """
        Get pandas DataFrame from process manifest
        """
        input_manifest = self.get_input_manifest(process_manifest.input)
        df = self.get_df_from_input_manifest(input_manifest)

        logger.info(f"Processing process manifest: {process_manifest.input}")
        # Process DataFrame
        for process in process_manifest.process_steps:
            process_class = self.get_class_from_name(process.df_process, DfProcess)
            process_instance = process_class(process.kwargs)
            df = process_instance.process(df)
            logger.info(f"Applied df process: {process.df_process}")

        return df

    def plot_from_process_manifest(self, process_manifest: DfProcessManifest, fig: Figure):
        """
        Plot from process manifest
        """
        if process_manifest.plotter is None:
            return

        df = self.get_df_from_process_manifest(process_manifest)

        logger.info(f"Plotting process manifest: {process_manifest.input}")
        plotter_class = self.get_class_from_name(process_manifest.plotter.plotter, DfPlotter)
        plotter_instance = plotter_class(process_manifest.plotter.kwargs)
        plotter_instance.plot(df, fig)
