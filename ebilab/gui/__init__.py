"""
ebilab.gui - 実験GUI管理モジュール

このモジュールは、実験のGUIアプリケーションを構築・管理するためのコンポーネントを提供します。

主要なコンポーネント:
- App: TkinterベースのGUIビュー
- ExperimentController: ViewとServiceを連携させるコントローラー
- launch_gui: 実験GUIを起動するための便利関数
"""

from .controller import ExperimentController, create_controller, launch_gui
from .view import View

__all__ = [
    "View",
    "ExperimentController",
    "create_controller",
    "launch_gui",
]
