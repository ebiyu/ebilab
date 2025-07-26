import asyncio
from logging import getLogger
import threading
from typing import Type, Dict, Any, Optional, List
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import pandas as pd

from ..api.experiment import BaseExperiment
from ..api.plotting import BasePlotter
from ..core.service import ExperimentService, ExperimentStatus
from .view import View

logger = getLogger(__name__)

class ExperimentController:
    """
    View と Service を結ぶコントローラークラス。
    UIイベントを処理し、実験サービスと連携します。
    アプリケーションの寿命全体を通じて存続します。
    """

    def __init__(self, experiment_classes: List[Type[BaseExperiment]]):
        self.experiment_classes = experiment_classes
        self.current_experiment_class: Optional[Type[BaseExperiment]] = None
        self.service: ExperimentService = ExperimentService()  # 単一のサービスインスタンス
        self.app: Optional[View] = None

        # データ記録
        self.experiment_data: List[Dict[str, Any]] = []

        # プロッター関連
        self.current_plotter: Optional[BasePlotter] = None
        self.available_plotters: List[Type[BasePlotter]] = []

    def initialize(self):
        """コントローラーの初期化"""
        # サービスを初期化（軽量初期化）
        self.service.initialize()
        
        # ステータス変更コールバックを設定
        self.service.add_status_callback(self._on_status_changed)
        
        # UIを作成
        self.app = View()

        # イベントハンドラーの設定
        self._setup_event_handlers()

        # 実験リストの初期化
        self._populate_experiment_list()

    def _setup_event_handlers(self):
        """イベントハンドラーの設定"""
        if not self.app:
            return

        # UIからのコールバックを設定
        self.app.on_experiment_selected = self.on_experiment_selected
        self.app.on_start_experiment = self.on_start_experiment
        self.app.on_stop_experiment = self.on_stop_experiment
        self.app.on_history_selected = self.on_experiment_history_selected

    def _populate_experiment_list(self):
        """実験リストをUIに設定"""
        if not self.app or not self.experiment_classes:
            return

        experiment_names = [cls.__name__ for cls in self.experiment_classes]
        self.app.set_experiment_list(experiment_names)

        # 最初の実験を選択
        if experiment_names:
            self.on_experiment_selected(experiment_names[0])

    def on_experiment_selected(self, experiment_name: str):
        """実験が選択されたときの処理"""
        for exp_class in self.experiment_classes:
            if exp_class.__name__ == experiment_name:
                self.current_experiment_class = exp_class
                break

        # 利用可能なプロッターを取得
        self._update_available_plotters()

        # UIの実験パラメータエリアを更新
        self._update_parameter_ui()

        # ログメッセージを追加
        if self.app:
            self.app.add_log_message(f"実験 '{experiment_name}' が選択されました。")

    def _update_available_plotters(self):
        """利用可能なプロッターを更新"""
        if not self.current_experiment_class:
            self.available_plotters = []
            return

        # 実験クラスに登録されたプロッターを取得
        if hasattr(self.current_experiment_class, "_plotters"):
            self.available_plotters = self.current_experiment_class._plotters.copy()
        else:
            self.available_plotters = []

        # デフォルトプロッターがない場合は、シンプルなプロッターを作成
        if not self.available_plotters:
            self.available_plotters = [self._create_default_plotter()]

    def _create_default_plotter(self):
        """デフォルトプロッターを作成"""

        class DefaultPlotter(BasePlotter):
            name = "default"

            def setup(self):
                if self.fig:
                    self._ax = self.fig.add_subplot(111)

            def update(self, df: pd.DataFrame):
                if hasattr(self, "_ax") and not df.empty:
                    self._ax.clear()

                    # 時間列があるかチェック
                    if "t" in df.columns:
                        x_data = df["t"]
                        x_label = "Time (s)"
                    else:
                        x_data = df.index
                        x_label = "Index"

                    # 数値列を探してプロット
                    numeric_columns = df.select_dtypes(include=["number"]).columns
                    for col in numeric_columns:
                        if col != "t":  # 時間列以外
                            self._ax.plot(x_data, df[col], label=col)
                            break

                    self._ax.set_xlabel(x_label)
                    self._ax.set_ylabel("Value")
                    self._ax.grid(True)
                    if len(numeric_columns) > 1:
                        self._ax.legend()

        return DefaultPlotter

    def _update_parameter_ui(self):
        """実験パラメータUIの更新"""
        if not self.current_experiment_class or not self.app:
            return

        self.app.set_experiment_parameters(self.current_experiment_class._get_option_fields())

    def on_start_experiment(self, params: Dict[str, Any]):
        """実験開始ボタンが押されたときの処理"""
        if not self.current_experiment_class or not self.app:
            return

        # 結果をクリア
        self.app.clear_results()
        self.experiment_data.clear()

        # プロッターを初期化
        self._initialize_plotter()

        # サービス経由で実験を開始
        self.service.start_experiment(self.current_experiment_class, params)

        # データストリームの監視を開始
        self._start_data_monitoring()

    def _on_status_changed(self, status):
        """サービスのステータス変更時の処理"""
        if not self.app:
            return
            
        # UIスレッドで状態を更新
        status_map = {
            ExperimentStatus.IDLE: "idle",
            ExperimentStatus.RUNNING: "running", 
            ExperimentStatus.STOPPING: "stopping",
            ExperimentStatus.FINISHED: "finished",
            ExperimentStatus.ERROR: "error"
        }
        
        ui_status = status_map.get(status, "idle")
        self.app.after(0, lambda: self.app.update_experiment_state(ui_status))

    def _initialize_plotter(self):
        """プロッターを初期化"""
        if not self.available_plotters or not self.app or not self.app.figure:
            return

        # 最初のプロッターを使用
        plotter_class = self.available_plotters[0]
        self.current_plotter = plotter_class()
        self.current_plotter.fig = self.app.figure

        # プロッターのセットアップを実行
        try:
            self.current_plotter.setup()
        except Exception as e:
            if self.app:
                self.app.add_log_message(f"プロッター初期化エラー: {e}")

    def _update_plot(self):
        """プロットの更新（プロッター使用）"""
        if not self.app or not self.current_plotter or len(self.experiment_data) < 1:
            return

        try:
            # DataFrameを作成
            df = pd.DataFrame(self.experiment_data)

            # 時間列を追加（存在しない場合）
            if "t" not in df.columns and len(self.experiment_data) > 0:
                # インデックスをベースにした時間列を追加
                df["t"] = range(len(df))

            # プロッターでプロットを更新
            self.current_plotter.update(df)

            # キャンバスを更新
            if self.app.canvas:
                self.app.canvas.draw()

        except Exception as e:
            if self.app:
                self.app.add_log_message(f"プロット更新エラー: {e}")
                # フォールバック: シンプルなプロット
                self._fallback_plot()

    def _fallback_plot(self):
        """フォールバック用のシンプルなプロット"""
        if not self.app or len(self.experiment_data) < 2:
            return

        # 時系列データとしてプロット
        times = []
        values = []

        for i, data in enumerate(self.experiment_data):
            times.append(i)  # インデックスを時間として使用
            # データから最初の数値を取得
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    values.append(value)
                    break
            else:
                values.append(0)  # 数値が見つからない場合は0

        self.app.update_plot(times, values, "Time", "Value", "実験データ")

    def _start_data_monitoring(self):
        """データストリームの監視を開始"""
        if not self.service or not self.service._experiment_active:
            return

        # 実験スレッドの準備を待つ
        def wait_and_start():
            import time
            max_wait = 5  # 最大5秒待機
            wait_time = 0
            
            while wait_time < max_wait:
                if self.service.loop and self.service._experiment_active:
                    asyncio.run_coroutine_threadsafe(self._monitor_data_stream(), self.service.loop)
                    break
                time.sleep(0.1)
                wait_time += 0.1
            else:
                if self.app:
                    self.app.after(0, lambda: self.app.add_log_message("データ監視の開始に失敗しました"))
        
        threading.Thread(target=wait_and_start, daemon=True).start()

    async def _monitor_data_stream(self):
        """データストリームを監視してUIを更新"""
        if not self.service:
            return

        try:
            async for data in self.service.get_data_stream():
                # データをリストに追加
                self.experiment_data.append(data)

                # UIスレッドでUIを更新
                if self.app:
                    self.app.after(0, lambda d=data: self._update_ui_with_data(d))

        except Exception as e:
            # データストリーム監視中にエラーが発生
            if self.app:
                self.app.after(0, lambda: self.app.add_log_message(f"データ監視エラー: {e}"))
                self.app.after(0, lambda: self.app.update_experiment_state("idle"))

    def _update_ui_with_data(self, data: Dict[str, Any]):
        """新しいデータでUIを更新"""
        if not self.app:
            return

        # 結果テーブルに行を追加
        self.app.add_result_row(data)

        # プロットを更新
        self._update_plot()

    def _update_plot(self):
        """プロットの更新"""
        if not self.app or len(self.experiment_data) < 2:
            return

        # 時系列データとしてプロット
        times = []
        values = []

        for i, data in enumerate(self.experiment_data):
            times.append(i)  # インデックスを時間として使用
            # データから最初の数値を取得
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    values.append(value)
                    break
            else:
                values.append(0)  # 数値が見つからない場合は0

        self.app.update_plot(times, values, "Time", "Value", "実験データ")

    def on_stop_experiment(self):
        """実験中断ボタンが押されたときの処理"""
        if not self.service or not self.app:
            return

        # サービス経由で実験を停止
        self.service.stop_experiment_sync()

    def on_experiment_history_selected(self, experiment_id: str):
        """実験履歴が選択されたときの処理"""
        if self.app:
            self.app.add_log_message(f"履歴実験 '{experiment_id}' が選択されました。")

        # 過去の実験データを読み込んでプロット
        self._load_and_plot_historical_data(experiment_id)

    def _load_and_plot_historical_data(self, experiment_id: str):
        """過去の実験データを読み込んでプロット"""
        if not self.app:
            return

        # 模擬的な履歴データ
        import random

        times = list(range(50))
        values = [random.random() * 10 for _ in times]

        self.app.update_plot(times, values, "Time", "Value", f"履歴データ: {experiment_id}")
        self.app.add_log_message(f"履歴データ '{experiment_id}' をプロットしました。")

    def run(self):
        """アプリケーションの実行"""
        if self.app:
            self.app.mainloop()

    def cleanup(self):
        """リソースのクリーンアップ"""
        # サービスをシャットダウン（実行中の実験も停止される）
        if self.service:
            self.service.shutdown()


# 使用例
def create_controller(experiment_classes: List[Type[BaseExperiment]]) -> ExperimentController:
    """コントローラーのファクトリー関数"""
    controller = ExperimentController(experiment_classes)
    controller.initialize()
    return controller


# コンビニエンス関数
def launch_gui(experiment_classes: List[Type[BaseExperiment]]):
    """GUIアプリケーションを起動"""
    controller = create_controller(experiment_classes)

    try:
        controller.run()
    finally:
        controller.cleanup()
