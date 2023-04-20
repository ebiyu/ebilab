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

@dataclasses.dataclass(frozen=True)
class IntField(OptionField):
    default: int
    max: Optional[int] = None
    min: Optional[int] = None

@dataclasses.dataclass(frozen=True)
class StrField(OptionField):
    default: str
    allow_blank: bool = False
