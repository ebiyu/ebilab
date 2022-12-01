import dataclasses
import abc
from typing import Optional

class OptionField(metaclass=abc.ABCMeta):
    pass

@dataclasses.dataclass(frozen=True)
class FloatField(OptionField):
    default: float
    max: Optional[float] = None
    min: Optional[float] = None

@dataclasses.dataclass(frozen=True)
class SelectField(OptionField):
    choices: list
    default_index: int = 0
