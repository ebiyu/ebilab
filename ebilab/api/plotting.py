from __future__ import annotations

from typing import Any

import pandas as pd

from .fields import OptionField


class BasePlotter:
    """
    可視化ロジックを定義するための基底クラス。

    Attributes:
        name: プロッターの表示名
        window_length: 表示対象のデータ長（末尾から何行分を update() に渡すか）。
                       None の場合は全履歴を渡す。
    """

    name: str = "Unnamed Plotter"
    window_length: int | None = None

    def __init__(self):
        """プロッターの初期化"""
        # パラメータフィールドの値をインスタンス変数として設定
        self._setup_fields()

        # matplotlib figure (コントローラーから設定される)
        self.fig = None

        # experiment instance (コントローラーから設定される)
        self.experiment = None

    @classmethod
    def _get_option_fields(cls) -> dict[str, Any]:
        """Return dict of field which inherits OptionField"""
        result = {}
        for attr_name in dir(cls):
            attr_value = getattr(cls, attr_name)
            if isinstance(attr_value, OptionField):
                result[attr_name] = getattr(cls, attr_name, None)
        return result

    def _setup_fields(self):
        """クラスに定義されたフィールドのデフォルト値を設定"""
        for attr_name in dir(self.__class__):
            attr_value = getattr(self.__class__, attr_name)
            # フィールドオブジェクトかチェック
            if hasattr(attr_value, "default"):
                # 既に値が設定されていなければデフォルト値を使用
                if not hasattr(self, attr_name):
                    if hasattr(attr_value, "choices") and hasattr(attr_value, "default_index"):
                        # SelectField の場合
                        setattr(self, attr_name, attr_value.choices[attr_value.default_index])
                    else:
                        # その他のフィールドの場合
                        setattr(self, attr_name, attr_value.default)

    def setup(self):
        """
        プロットの初期設定を行う。プロットがアクティブになった際に一度だけ呼ばれる。
        """
        pass

    def update(self, df: pd.DataFrame):
        """
        新しいデータを受け取り、プロットを更新する。

        Args:
            df: 実験データのDataFrame。
        """
        raise NotImplementedError("You must implement the 'update' method.")

    def get_window_length(self) -> int | None:
        """
        Override to dynamically set window_length.

        Returns:
            int | None: window_length value. Default returns self.window_length.
        """
        return self.window_length


class SimpleXYPlotter(BasePlotter):
    """
    軸名を指定するだけで使える汎用 Plotter。

    Example:
        class MyExperiment(BaseExperiment):
            plotters = [
                SimpleXYPlotter("t", "v"),
                SimpleXYPlotter("t", ["v", "v2"]),
            ]
    """

    def __init__(
        self,
        x_column: str,
        y_column: str | list[str],
        *,
        name: str | None = None,
        window_length: int | None = None,
    ):
        super().__init__()
        self.x_column = x_column
        self.y_columns: list[str] = [y_column] if isinstance(y_column, str) else list(y_column)
        if name is not None:
            self.name = name
        elif len(self.y_columns) == 1:
            self.name = f"simple({x_column}, {self.y_columns[0]})"
        else:
            self.name = f"simple({x_column}, [{', '.join(self.y_columns)}])"
        self.window_length = window_length

    def setup(self):
        if self.fig:
            self._ax = self.fig.add_subplot(111)

    def update(self, df):
        if not hasattr(self, "_ax") or df.empty:
            return
        if self.x_column not in df.columns:
            return
        available = [c for c in self.y_columns if c in df.columns]
        if not available:
            return
        self._ax.clear()
        for col in available:
            self._ax.plot(df[self.x_column], df[col], label=col)
        self._ax.set_xlabel(self.x_column)
        if len(available) == 1:
            self._ax.set_ylabel(available[0])
        else:
            self._ax.legend()
        self._ax.grid(True)
