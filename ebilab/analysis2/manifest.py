from __future__ import annotations

import dataclasses
from typing import Any


class ManifestParseError(Exception):
    pass


@dataclasses.dataclass
class DfProcessStep:
    df_process: str
    kwargs: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DfProcessStep:
        return cls(df_process=data["df_process"], kwargs=data.get("kwargs", {}))

    def as_dict(self) -> dict[str, Any]:
        if self.kwargs:
            return {"df_process": self.df_process, "kwargs": self.kwargs}
        return {"df_process": self.df_process}


@dataclasses.dataclass
class FileProcessStep:
    file_process: str
    kwargs: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileProcessStep:
        return cls(file_process=data["file_process"], kwargs=data.get("kwargs", {}))

    def as_dict(self) -> dict[str, Any]:
        if self.kwargs:
            return {"file_process": self.file_process, "kwargs": self.kwargs}
        return {"file_process": self.file_process}


@dataclasses.dataclass
class PlotterStep:
    plotter: str
    kwargs: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotterStep:
        return cls(plotter=data["plotter"], kwargs=data.get("kwargs", {}))

    def as_dict(self) -> dict[str, Any]:
        if self.kwargs:
            return {"plotter": self.plotter, "kwargs": self.kwargs}
        return {"plotter": self.plotter}


@dataclasses.dataclass
class InputManifest:
    original: str  # posix path relative to "original" directory
    file_process_steps: list[FileProcessStep] = dataclasses.field(default_factory=list)
    df_process_steps: list[DfProcessStep] = dataclasses.field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InputManifest:
        return cls(
            original=data["original"],
            file_process_steps=[
                FileProcessStep.from_dict(step) for step in data.get("file_process_steps", [])
            ],
            df_process_steps=[
                DfProcessStep.from_dict(step) for step in data.get("df_process_steps", [])
            ],
        )

    def as_dict(self) -> dict[str, Any]:
        result: Any = {"original": self.original}
        if self.file_process_steps:
            result["file_process_steps"] = [step.as_dict() for step in self.file_process_steps]
        if self.df_process_steps:
            result["df_process_steps"] = [step.as_dict() for step in self.df_process_steps]
        return result


@dataclasses.dataclass
class DfProcessManifest:
    input: str
    process_steps: list[DfProcessStep] = dataclasses.field(default_factory=list)
    plotter: PlotterStep | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DfProcessManifest:
        instance = cls(
            input=data["input"],
            process_steps=[DfProcessStep.from_dict(step) for step in data.get("process_steps", [])],
            plotter=None,
        )
        if plotter := data.get("plotter"):
            instance.plotter = PlotterStep.from_dict(plotter)
        return instance

    def as_dict(self) -> dict[str, Any]:
        result: Any = {"input": self.input}
        if self.process_steps:
            result["process_steps"] = [step.as_dict() for step in self.process_steps]
        if self.plotter:
            result["plotter"] = self.plotter.as_dict()
        return result


@dataclasses.dataclass
class Manifest:
    version: str
    inputs: dict[str, InputManifest]
    outputs: dict[str, DfProcessManifest]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Manifest:
        return cls(
            version=data["version"],
            inputs={
                name: InputManifest.from_dict(input)
                for name, input in data.get("inputs", {}).items()
            },
            outputs={
                name: DfProcessManifest.from_dict(output)
                for name, output in data.get("outputs", {}).items()
            },
        )

    def as_dict(self) -> dict[str, Any]:
        result: Any = {"version": self.version}
        if self.inputs:
            result["inputs"] = {name: input.as_dict() for name, input in self.inputs.items()}
        if self.outputs:
            result["outputs"] = {name: output.as_dict() for name, output in self.outputs.items()}
        return result
