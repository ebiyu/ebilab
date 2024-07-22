from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Callable, Any
import importlib
import sys
import inspect
import uuid
from logging import getLogger

from .util import Event
from .protocol import ExperimentProtocol, ExperimentProtocolGroup

logger = getLogger(__name__)

def postprocess_experiments(experiments: list[ExperimentProtocolInfo]):
    """
    workaround for bug
    """
    for experiment in experiments:
        if  experiment.children is not None:
            postprocess_experiments(experiment.children)

        if experiment.protocol is not None and experiment.protocol.plotter_classes is None:
            experiment.protocol.plotter_classes = []

@dataclasses.dataclass
class ExperimentProtocolInfo:
    label: str
    protocol: type[ExperimentProtocol] | None = None
    children: list[ExperimentProtocolInfo] | None = None
    key: str = dataclasses.field(default_factory=lambda:str(uuid.uuid4()))
    filepath: Path | None = None
    module_name: str | None = None
    module: Any = None # module

    @classmethod
    def from_experiment(cls, obj: type[ExperimentProtocol] | ExperimentProtocolGroup)  -> ExperimentProtocolInfo:
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

ExperimentManagerHandler = Callable[[list[type[ExperimentProtocol]]], None]
class ExperimentManager:
    """
    manages experiment protocols
    """

    _experiments: list[ExperimentProtocolInfo]

    def __init__(self, experiments: list[ExperimentProtocolInfo]):
        self.changed_event = Event[list[ExperimentProtocolInfo]]()
        self.update_experiments(experiments)

    @classmethod
    def discover(cls, dir: Path) -> ExperimentManager:
        target = Path(dir).resolve()

        if not target.exists():
            raise RuntimeError(f"File {dir} does not exist")

        if not target.is_dir():
            raise RuntimeError(f"File {dir} is not directory")

        # Discover protocols
        # TODO: support experiment group
        sys.path.append(str(target.parent))
        files = target.glob("*.py")
        protocols: list[ExperimentProtocolInfo] = []
        for file in files:
            module_name = target.name + "." + file.stem
            mod = importlib.import_module(module_name)

            for _, obj in inspect.getmembers(mod):
                if inspect.isclass(obj) and issubclass(obj, ExperimentProtocol) and obj.__name__ != "ExperimentProtocol":
                    # if the class is protocol
                    logger.debug(f"Loaded {obj.__name__} from {file}")
                    loaded_experiment = ExperimentProtocolInfo(
                        protocol=obj,
                        label=obj.get_summary(),
                        key=str(uuid.uuid4()),
                        filepath=file,
                        module_name=module_name,
                        module=mod,
                    )
                    protocols.append(loaded_experiment)

        # TODO: change sort method
        protocols.sort(key=lambda p:p.protocol.name) # type: ignore

        logger.info(f"Found {len(protocols)} protocols")

        # FIXME: mypy error
        discovered: list[ExperimentProtocolInfo | ExperimentProtocolGroupInfo] = protocols # type: ignore

        return cls(discovered)

    @classmethod
    def from_experiments(cls, experiments: list[type[ExperimentProtocol]]) -> ExperimentManager:
        return cls(list(map(ExperimentProtocolInfo.from_experiment, experiments)))

    def update_experiments(self, experiments: list[ExperimentProtocolInfo]):
        self._experiments = experiments
        postprocess_experiments(experiments)
        # self._update_key(self._experiments, "")
        self.changed_event.notify(self._experiments)

    # def _update_key(self, experiments: list[type[ExperimentProtocol]], key):
    #     for i, experiment in enumerate(experiments):
    #         new_key = f"{key}.{i}"
    #         if isinstance(experiment, ExperimentProtocolGroup):
    #             self._insert_experiments(id, experiment.protocols, new_key)
    #             continue
    #         else:
    #             # FIXME: updating experiment class may be bad practice, fix type definition
    #             experiment.key = new_key # type: ignore

    @property
    def experiments(self):
        return self._experiments

    def get_experiment_by_key(self, key: str) -> type[ExperimentProtocol] | None:
        """
        Get ExperimentProcol class by key
        Args:
            key(str): like ".1.2.1", ".2", ...
        """
        def _get_by_key(key: str, info_list: list[ExperimentProtocolInfo]) -> ExperimentProtocolInfo | None:
            # recursive lookup
            for info in info_list:
                if info.key == key:
                    return info
                if info.children is not None:
                    found = _get_by_key(key, info.children)
                    if found is not None:
                        return found
            return None

        info = _get_by_key(key, self._experiments)
        if info is None:
            return None
        if info.protocol is None:
            return None
        return info.protocol
