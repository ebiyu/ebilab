from __future__ import annotations

import abc
import dataclasses
import tkinter as tk
from tkinter import ttk
from typing import Any


class InvalidInputError(Exception):
    pass


class OptionField(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def build_widget(self, root: tk.Widget) -> tuple[tk.Variable, tk.Widget]:
        """
        Returns: tuple of (tk.Variable, tk.Widget)
        """
        raise NotImplementedError("build_widget method must be implemented in subclass")

    @abc.abstractmethod
    def get_from_widget(self, var: tk.Variable) -> Any:
        raise NotImplementedError("get_value method must be implemented in subclass")

    @abc.abstractmethod
    def set_to_widget(self, var: tk.Variable, value: Any) -> None:
        raise NotImplementedError("set_to_widget method must be implemented in subclass")

    def is_valid(self, variable: tk.Variable) -> Any:
        try:
            self.get_from_widget(variable)
            return True
        except InvalidInputError:
            return False

    def get_default(self) -> Any:
        if hasattr(self, "default"):
            return self.default
        raise NotImplementedError(
            "default attribute or get_default() method must be implemented in subclas"
        )


@dataclasses.dataclass(frozen=True)
class FloatField(OptionField):
    default: float
    max: float | None = None
    min: float | None = None

    def build_widget(self, root: tk.Widget) -> tuple[tk.Variable, tk.Widget]:
        var = tk.StringVar(value=str(self.default))
        widget = tk.Entry(root, textvariable=var)
        return var, widget

    def get_from_widget(self, var: tk.Variable) -> Any:
        try:
            val = float(var.get())
        except ValueError:
            raise InvalidInputError(f"{var.get()} is not float.")
        if self.min is not None and val < self.min:
            raise InvalidInputError(f"{val} < {self.min}.")
        if self.max is not None and val > self.max:
            raise InvalidInputError(f"{val} > {self.max}.")
        return val

    def set_to_widget(self, var: tk.Variable, value: Any) -> None:
        var.set(str(value))


@dataclasses.dataclass(frozen=True)
class SelectField(OptionField):
    choices: list[Any]
    default_index: int = 0

    def build_widget(self, root: tk.Widget) -> tuple[tk.Variable, tk.Widget]:
        var = tk.StringVar(value=str(self.choices[self.default_index]))
        widget = ttk.Combobox(root, textvariable=var, state="readonly", values=self.choices)
        return var, widget

    def get_from_widget(self, var: tk.Variable) -> Any:
        if len(self.choices) == 0:
            raise ValueError("SelectField has no choices.")
        if isinstance(self.choices[0], int):
            return int(var.get())
        elif isinstance(self.choices[0], float):
            return float(var.get())
        else:
            return var.get()

    def set_to_widget(self, var: tk.Variable, value: Any) -> None:
        var.set(str(value))  # TODO: test this


@dataclasses.dataclass(frozen=True)
class IntField(OptionField):
    default: int
    max: int | None = None
    min: int | None = None

    def build_widget(self, root: tk.Widget) -> tuple[tk.Variable, tk.Widget]:
        var = tk.StringVar(value=str(self.default))
        widget = tk.Entry(root, textvariable=var)
        return var, widget

    def get_from_widget(self, var: tk.Variable) -> Any:
        try:
            val = int(var.get())
        except ValueError:
            raise InvalidInputError(f"{var.get()} is not int.")
        if self.min is not None and val < self.min:
            raise InvalidInputError(f"{val} < {self.min}.")
        if self.max is not None and val > self.max:
            raise InvalidInputError(f"{val} > {self.max}.")
        return val

    def set_to_widget(self, var: tk.Variable, value: Any) -> None:
        var.set(str(value))


@dataclasses.dataclass(frozen=True)
class StrField(OptionField):
    default: str
    allow_blank: bool = False

    def build_widget(self, root: tk.Widget) -> tuple[tk.Variable, tk.Widget]:
        var = tk.StringVar(root, value=str(self.default))
        widget = ttk.Entry(root, textvariable=var)
        return var, widget

    def get_from_widget(self, var: tk.Variable) -> Any:
        val = var.get()
        if not self.allow_blank and val == "":
            raise InvalidInputError("Blank string is not allowed.")
        return val

    def set_to_widget(self, var: tk.Variable, value: Any) -> None:
        var.set(value)


@dataclasses.dataclass(frozen=True)
class BoolField(OptionField):
    default: bool = False

    def build_widget(self, root: tk.Widget) -> tuple[tk.Variable, tk.Widget]:
        var = tk.BooleanVar(value=self.default)
        widget = tk.Checkbutton(root, variable=var)
        return var, widget

    def get_from_widget(self, var: tk.Variable) -> Any:
        return var.get()

    def set_to_widget(self, var: tk.Variable, value: Any) -> None:
        var.set(value)
