from __future__ import annotations

from logging import getLogger
from typing import Any

from .fields import OptionField
from .plotting import BasePlotter

logger = getLogger(__name__)


class BaseExperiment:
    """
    Inherit this class to define an experiment.
    """

    columns: list[str] = []  # Columns to be saved in CSV files
    name: str = "experiment"  # Base name for the experiment (used in file names)

    _plotters: list[type[BasePlotter]] = []  # This will be set by @register_plotter decorator

    @classmethod
    def register_plotter(cls, plotter_class: type[BasePlotter]) -> type[BasePlotter]:
        """decorator to register a plotter class"""
        logger.debug(f"Registering plotter: {plotter_class.__name__} in {cls.__name__}")
        if not issubclass(plotter_class, BasePlotter):
            raise TypeError("Registered class must be a subclass of BasePlotter.")
        if not hasattr(cls, "_plotters"):
            cls._plotters = []
        cls._plotters.append(plotter_class)
        return plotter_class

    def __init__(self, options):
        self._setup_option_value(options)

    @classmethod
    def _get_option_fields(cls) -> dict[str, Any]:
        """Return dict of field which inherits OptionField"""
        result = {}
        for attr_name in dir(cls):
            attr_value = getattr(cls, attr_name)
            if isinstance(attr_value, OptionField):
                result[attr_name] = getattr(cls, attr_name, None)
        return result

    def _setup_option_value(self, options):
        """Overwrite OptionField values with provided options"""
        self._options = options
        for key, value in options.items():
            if hasattr(self, key) and isinstance(getattr(self, key), OptionField):
                setattr(self, key, value)
            else:
                logger.warning(
                    f"Option '{key}' is not a valid OptionField in {self.__class__.__name__}."
                )

    async def setup(self):
        """Override this method to initialize the experiment."""
        pass

    async def steps(self):
        """Override this method to define the experiment steps."""
        raise NotImplementedError("You must implement the 'steps' async generator method.")
        yield

    async def cleanup(self):
        """Override this method to define the cleanup steps."""
        pass
