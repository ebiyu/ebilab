from __future__ import annotations

import dataclasses
import importlib
import inspect
import sys
import uuid
from logging import getLogger
from pathlib import Path
from typing import Any

from .protocol import ExperimentProtocol, ExperimentProtocolGroup
from .util import Event

logger = getLogger(__name__)


@dataclasses.dataclass
class ExperimentProtocolInfo:
    label: str
    protocol: type[ExperimentProtocol] | None = None
    children: list[ExperimentProtocolInfo] | None = None
    key: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    filepath: Path | None = None
    module_name: str | None = None
    module: Any = None  # module

    @classmethod
    def from_experiment(
        cls, obj: type[ExperimentProtocol] | ExperimentProtocolGroup
    ) -> ExperimentProtocolInfo:
        if isinstance(obj, ExperimentProtocolGroup):
            group = obj
            return ExperimentProtocolInfo(
                label=group.name,
                children=list(map(cls.from_experiment, group.protocols)),
            )
        else:
            experiment = obj
            return ExperimentProtocolInfo(
                label=experiment.get_summary(),
                protocol=experiment,
                key=str(uuid.uuid4()),
            )


class ExperimentManager:
    """
    manages experiment protocols
    """

    _experiments: list[ExperimentProtocolInfo]

    def __init__(self, experiments: list[ExperimentProtocolInfo]):
        self.changed_event: Event[list[ExperimentProtocolInfo]] = Event()
        self.update_experiments(experiments)

    @classmethod
    def discover(cls, dir: Path) -> ExperimentManager:
        target = Path(dir).resolve()

        if not target.exists():
            raise RuntimeError(f"File {dir} does not exist")

        if not target.is_dir():
            raise RuntimeError(f"File {dir} is not directory")

        # Discover protocols
        sys.path.append(str(target.parent))
        protocols = cls._read_file("", target)

        # TODO: sort by name
        # protocols.sort(key=lambda p: p.protocol.name)  # type: ignore

        logger.info(f"Found {len(protocols)} protocols")

        return cls(protocols)

    @classmethod
    def _read_file(cls, baseModule: str, file: Path) -> list[ExperimentProtocolInfo]:
        if file.is_dir():
            files = file.glob("*")
            children = []
            if baseModule == "":
                baseModule = file.name
            else:
                baseModule = baseModule + "." + file.name

            for f in files:
                children.extend(cls._read_file(baseModule, f))

            if len(children) == 0:
                return []
            return [
                ExperimentProtocolInfo(
                    label=file.name,
                    children=children,
                    key=str(uuid.uuid4()),
                )
            ]

        if file.suffix != ".py":
            return []

        ret: list[ExperimentProtocolInfo] = []
        module_name = baseModule + "." + file.stem
        mod = importlib.import_module(module_name)

        for _, obj in inspect.getmembers(mod):
            if (
                inspect.isclass(obj)
                and issubclass(obj, ExperimentProtocol)
                and obj.__name__ != "ExperimentProtocol"
            ):
                # if the class is protocol, add to list
                logger.debug(f"Loaded {obj.__name__} from {file}")
                loaded_experiment = ExperimentProtocolInfo(
                    protocol=obj,
                    label=obj.get_summary(),
                    key=str(uuid.uuid4()),
                    filepath=file,
                    module_name=module_name,
                    module=mod,
                )
                ret.append(loaded_experiment)
        return ret

    @classmethod
    def from_experiments(cls, experiments: list[type[ExperimentProtocol]]) -> ExperimentManager:
        return cls(list(map(ExperimentProtocolInfo.from_experiment, experiments)))

    def reload(self, key: str) -> None:
        """
        Reload experiment protocol
        """
        experiment = self.get_experiment_by_key(key)
        if experiment is None:
            return None
        protocol = experiment.protocol
        if protocol is None:
            return None

        module_name = experiment.module_name
        if module_name is None:
            return

        # reload module
        logger.info(f"Reloading {module_name}")
        module = importlib.import_module(module_name)
        importlib.reload(module)
        logger.info(f"Reloaded {module_name}")

        # refresh
        experiment.module = module
        for _, obj in inspect.getmembers(module):
            if hasattr(obj, "__name__") and obj.__name__ == protocol.__name__:
                experiment.protocol = obj
                logger.info(f"Reloaded {protocol.__name__}")

    def update_experiments(self, experiments: list[ExperimentProtocolInfo]) -> None:
        self._experiments = experiments
        self.changed_event.notify(self._experiments)

    @property
    def experiments(self) -> list[ExperimentProtocolInfo]:
        return self._experiments

    def get_experiment_by_key(self, key: str) -> ExperimentProtocolInfo | None:
        """
        Get ExperimentProcol class by key
        Args:
            key(str): like ".1.2.1", ".2", ...
        """

        def _get_by_key(
            key: str, info_list: list[ExperimentProtocolInfo]
        ) -> ExperimentProtocolInfo | None:
            # recursive lookup
            for info in info_list:
                if info.key == key:
                    return info
                if info.children is not None:
                    found = _get_by_key(key, info.children)
                    if found is not None:
                        return found
            return None

        return _get_by_key(key, self._experiments)
