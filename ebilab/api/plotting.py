from __future__ import annotations

from typing import Any

import pandas as pd

from .fields import OptionField


class BasePlotter:
    """
    可視化ロジックを定義するための基底クラス。
    """

    name: str = "Unnamed Plotter"

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
