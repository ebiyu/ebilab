from __future__ import annotations

from pathlib import Path
from typing import Callable
from .util import Event
from .protocol import ExperimentProtocol, ExperimentProtocolGroup

def prepare_experiments(experiments):
    for experiment in experiments:
        if isinstance(experiment, ExperimentProtocolGroup):
            prepare_experiments(experiment.protocols)
            continue

        if experiment.plotter_classes is None:
            experiment.plotter_classes = []

ExperimentManagerHandler = Callable[[list[type[ExperimentProtocol]]], None]
class ExperimentManager:
    _experiments: list[type[ExperimentProtocol]]

    def __init__(self, experiments: list[type[ExperimentProtocol]]):
        self.update_experiments(experiments)
        self.changed_event = Event[list[type[ExperimentProtocol]]]()

    @classmethod
    def discover(cls, dir: Path) -> ExperimentManager:
        # TODO: implement
        raise NotImplementedError()

    def update_experiments(self, experiments: list[type[ExperimentProtocol]]):
        self._experiments = experiments
        prepare_experiments(experiments)
        self._update_key(self._experiments, "")
        self.changed_event.notify(self._experiments)

    def _update_key(self, experiments: list[type[ExperimentProtocol]], key):
        for i, experiment in enumerate(experiments):
            new_key = f"{key}.{i}"
            if isinstance(experiment, ExperimentProtocolGroup):
                self._insert_experiments(id, experiment.protocols, new_key)
                continue
            else:
                # FIXME: updating experiment class may be bad practice, fix type definition
                experiment.key = new_key # type: ignore

    @property
    def experiments(self):
        return self._experiments

    def get_by_ids(self, ids: list[int]) -> type[ExperimentProtocol] | None:
        experiments = self._experiments
        for id in ids:
            experiment = experiments[id]
            if not isinstance(experiment, ExperimentProtocolGroup):
                return experiment
            experiments = experiment.protocols
        return None

    def get_by_key(self, key: str) -> type[ExperimentProtocol] | None:
        """
        Get ExperimentProcol class by key
        Args:
            key(str): like ".1.2.1", ".2", ...
        """
        ids_str = key.split(".")
        ids = list(map(int, ids_str))
        return self.get_by_ids(ids[1:])

