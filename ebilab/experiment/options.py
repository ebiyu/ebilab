from __future__ import annotations

import abc
import dataclasses
from typing import Any


class OptionField(metaclass=abc.ABCMeta):
    pass


@dataclasses.dataclass(frozen=True)
class FloatField(OptionField):
    default: float
    max: float | None = None
    min: float | None = None


@dataclasses.dataclass(frozen=True)
class SelectField(OptionField):
    choices: list[Any]
    default_index: int = 0


@dataclasses.dataclass(frozen=True)
class IntField(OptionField):
    default: int
    max: int | None = None
    min: int | None = None


@dataclasses.dataclass(frozen=True)
class StrField(OptionField):
    default: str
    allow_blank: bool = False


@dataclasses.dataclass(frozen=True)
class BoolField(OptionField):
    default: bool = False
