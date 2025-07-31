from __future__ import annotations

import datetime
import queue
from logging import Handler, LogRecord, getLogger
from typing import Any

import pandas as pd

from ..api.experiment import BaseExperiment
from ..api.plotting import BasePlotter
from ..core.service import ExperimentService, ExperimentStatus
from .view import View

logger = getLogger(__name__)


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


class TkinterLogHandler(Handler):
    """A simple handler to add log to Queue"""

    def __init__(self):
        super().__init__()
        self.log_queue = queue.Queue()

    def emit(self, record: LogRecord):
        """ログレコードをキューに追加するだけ"""
        try:
            # ログメッセージをフォーマット
            timestamp = datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            level = record.levelname
            message = record.getMessage()
            formatted_message = f"{timestamp} - {level} - {message}\n"

            # キューにメッセージを追加
            self.log_queue.put(formatted_message)
        except Exception:
            # ハンドラー内でエラーが発生してもアプリケーションを止めない
            pass


class ExperimentController:
    """
    View と Service を結ぶコントローラークラス。
    UIイベントを処理し、実験サービスと連携します。
    アプリケーションの寿命全体を通じて存続します。
    """

    def __init__(self, experiment_classes: list[type[BaseExperiment]]):
        self.experiment_classes = experiment_classes
        self.current_experiment_class: type[BaseExperiment] | None = None
        self.current_plotter_class: type[BasePlotter] | None = None
        self.service: ExperimentService = ExperimentService()  # 単一のサービスインスタンス
        self.app: View | None = None

        # データ記録
        self.experiment_data: list[dict[str, Any]] = []

        # プロッター関連
        self.current_plotter: BasePlotter | None = None
        self.available_plotters: list[type[BasePlotter]] = []

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

        # ログハンドラーを設定
        self._setup_logging()

        # Timerを使って定期的にUIを更新
        self.app.after(100, self._after_callback_update)

        # 実験リストの初期化
        self._populate_experiment_list()

    def _setup_event_handlers(self):
        """イベントハンドラーの設定"""
        if not self.app:
            return

        # UIからのコールバックを設定
        self.app.on_experiment_selected = self.on_experiment_selected
        self.app.on_plotter_selected = self.on_plotter_selected
        self.app.on_plotter_parameter_changed = self.on_plotter_parameter_changed
        self.app.on_start_experiment = self.on_start_experiment
        self.app.on_debug_experiment = self.on_debug_experiment
        self.app.on_stop_experiment = self.on_stop_experiment
        self.app.on_sync = self.on_sync
        self.app.on_history_selected = self.on_experiment_history_selected

    def _after_callback_update(self):
        """定期的にUIを更新するためのコールバック"""
        if not self.app:
            return

        try:
            self._on_timer_update_log()
            has_new_data = self.on_timer_update_experiment_data()
            if has_new_data:
                self._update_plot()
        finally:
            # 再度呼び出す
            self.app.after(100, self._after_callback_update)

    def _setup_logging(self):
        # Setup logging
        import logging

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(formatter)

        logger = logging.getLogger("ebilab")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Setup custom log handler for Tkinter (attach to root logger)
        self.log_handler = TkinterLogHandler()
        self.log_handler.setLevel(logging.DEBUG)
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)

        logger.info("Loggging initialized for ebilab GUI.")

    def _populate_experiment_list(self):
        """実験リストをUIに設定"""
        if not self.app or not self.experiment_classes:
            return

        experiment_names = [cls.name for cls in self.experiment_classes]
        self.app.set_experiment_list(experiment_names)

        # 最初の実験を選択
        if experiment_names:
            self.on_experiment_selected(experiment_names[0])

    def _on_timer_update_log(self):
        for _ in range(50):
            try:
                message = self.log_handler.log_queue.get_nowait()
                self.app._append_log_to_text(message)
            except queue.Empty:
                break

    def on_timer_update_experiment_data(self) -> bool:
        """実験データを更新し、新しいデータがあったかどうかを返す"""
        if self.service.data_queue is None:
            return False

        has_new_data = False
        for _ in range(50):
            try:
                data = self.service.data_queue.get_nowait()
                self.experiment_data.append(data)
                self._update_ui_with_data(data)
                has_new_data = True
            except queue.Empty:
                break

        return has_new_data

    def on_experiment_selected(self, experiment_name: str):
        """実験が選択されたときの処理"""
        for exp_class in self.experiment_classes:
            if exp_class.name == experiment_name:
                self.current_experiment_class = exp_class
                break

        # 利用可能なプロッターを取得
        self._update_available_plotters()

        # UIの実験パラメータエリアを更新
        self._update_parameter_ui()

        # Update result table by clearing it
        self._initialize_experiment_result_table()

        # ログメッセージを追加
        logger.info(f"Selected experiment '{experiment_name}'")

    def _update_available_plotters(self):
        """利用可能なプロッターを更新"""
        if not self.current_experiment_class:
            logger.warning("No current experiment class set.")
            self.available_plotters = []
            return

        # 実験クラスに登録されたプロッターを取得
        if hasattr(self.current_experiment_class, "_plotters"):
            self.available_plotters = self.current_experiment_class._plotters.copy()
            logger.info(
                f"Available plotters for {self.current_experiment_class.__name__}: "
                f"{[p.name for p in self.available_plotters]}"
            )
        else:
            logger.warning("`_plotters` attribute not found in experiment class.")
            self.available_plotters = []

        # デフォルトプロッターがない場合は、シンプルなプロッターを作成
        if not self.available_plotters:
            logger.warning("No plotters available, using default plotter.")
            self.available_plotters = [DefaultPlotter]

        # UIのプロッターリストを更新
        self._update_plotter_ui()

    def _update_plotter_ui(self):
        """プロッターUIの更新"""
        if not self.app:
            return

        # プロッターリストを設定
        plotter_names = [plotter.name for plotter in self.available_plotters]
        self.app.set_plotter_list(plotter_names)

        # 最初のプロッターを選択
        if plotter_names:
            self.on_plotter_selected(plotter_names[0])

    def on_plotter_selected(self, plotter_name: str):
        """プロッターが選択されたときの処理"""
        for plotter_class in self.available_plotters:
            if plotter_class.name == plotter_name:
                self.current_plotter_class = plotter_class
                break

        # プロッターパラメータUIを更新
        self._update_plotter_parameter_ui()

        # 実験中でもプロッターを即座に切り替え
        if self.app and self.app.figure:
            self._initialize_plotter()
            # 既存のデータでプロットを更新
            if self.experiment_data:
                self._update_plot()

        logger.info(f"Selected plotter '{plotter_name}'")

    def on_plotter_parameter_changed(self):
        """プロッターパラメータが変更されたときの処理"""
        if self.current_plotter and self.app:
            # 現在のプロッターのパラメータを更新
            plotter_params = self.app.get_plotter_parameters()
            for key, value in plotter_params.items():
                if hasattr(self.current_plotter, key):
                    # 型変換を行う
                    field = getattr(self.current_plotter_class, key, None)
                    if field:
                        try:
                            if hasattr(field, "default"):
                                # フィールドの型に基づいて適切に変換
                                if isinstance(field.default, float):
                                    value = float(value)
                                elif isinstance(field.default, int):
                                    value = int(value)
                                elif isinstance(field.default, bool):
                                    value = bool(value)
                            setattr(self.current_plotter, key, value)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to set plotter parameter '{key}': {e}")

            # プロットを再描画
            if self.experiment_data:
                self._update_plot()

            logger.debug("Plotter parameters updated")

    def _update_plotter_parameter_ui(self):
        """プロッターパラメータUIの更新"""
        if not self.current_plotter_class or not self.app:
            return

        self.app.set_plotter_parameters(self.current_plotter_class._get_option_fields())

    def _update_parameter_ui(self):
        """実験パラメータUIの更新"""
        if not self.current_experiment_class or not self.app:
            return

        self.app.set_experiment_parameters(self.current_experiment_class._get_option_fields())

    def _initialize_experiment_result_table(self):
        """実験結果テーブルの初期化"""
        if not self.app:
            return

        self.app.clear_results()
        self.app.set_result_columns(["time", "t"] + self.current_experiment_class.columns)

        self.experiment_data.clear()

    def on_start_experiment(self, params: dict[str, Any]):
        """実験開始ボタンが押されたときの処理"""
        if not self.current_experiment_class or not self.app:
            return

        # 結果をクリア
        self._initialize_experiment_result_table()
        self.experiment_data.clear()

        # プロッターを初期化
        self._initialize_plotter()

        # サービス経由で実験を開始
        self.service.start_experiment(self.current_experiment_class, params)

    def on_debug_experiment(self, params: dict[str, Any]):
        """デバッグ実行ボタンが押されたときの処理"""
        if not self.current_experiment_class or not self.app:
            return

        # 結果をクリア
        self._initialize_experiment_result_table()
        self.experiment_data.clear()

        # プロッターを初期化
        self._initialize_plotter()

        # サービス経由でデバッグモードで実験を開始
        self.service.start_experiment(self.current_experiment_class, params, debug_mode=True)

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
            ExperimentStatus.ERROR: "error",
        }

        ui_status = status_map.get(status, "idle")
        self.app.after(0, lambda: self.app.update_experiment_state(ui_status))

    def _initialize_plotter(self):
        """プロッターを初期化"""
        if not self.current_plotter_class or not self.app or not self.app.figure:
            return

        # プロッターのインスタンスを作成
        self.current_plotter = self.current_plotter_class()
        self.current_plotter.fig = self.app.figure

        # プロッターパラメータを設定
        plotter_params = self.app.get_plotter_parameters()
        for key, value in plotter_params.items():
            if hasattr(self.current_plotter, key):
                # 型変換を行う
                field = getattr(self.current_plotter_class, key, None)
                if field:
                    try:
                        if hasattr(field, "default"):
                            # フィールドの型に基づいて適切に変換
                            if isinstance(field.default, float):
                                value = float(value)
                            elif isinstance(field.default, int):
                                value = int(value)
                            elif isinstance(field.default, bool):
                                value = bool(value)
                        setattr(self.current_plotter, key, value)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to set plotter parameter '{key}': {e}")

        # プロッターのセットアップを実行
        try:
            self.current_plotter.fig.clear()
            self.current_plotter.setup()
        except Exception as e:
            logger.error(f"プロッター初期化エラー: {e}")

        logger.info(f"Using plotter: {self.current_plotter.name}")

    def _update_plot(self):
        """Update plot using the current plotter"""
        if not self.app or not self.current_plotter or len(self.experiment_data) < 1:
            logger.debug("Skipping _update_plot()")
            return

        try:
            df = pd.DataFrame(
                self.experiment_data, columns=["time", "t"] + self.current_experiment_class.columns
            )
            if df.empty:
                logger.debug("No data to plot")
                return
            self.current_plotter.update(df)
            if self.app.canvas:
                self.app.canvas.draw()
        except Exception:
            logger.exception("Error updating plot")

    def _update_ui_with_data(self, data: dict[str, Any]):
        """新しいデータでUIを更新"""
        if not self.app:
            return

        # 結果テーブルに行を追加
        self.app.add_result_row(data)

    def on_stop_experiment(self):
        """実験中断ボタンが押されたときの処理"""
        if not self.service or not self.app:
            return

        # サービス経由で実験を停止
        self.service.stop_experiment()

    def on_sync(self):
        """Syncボタンが押されたときの処理"""
        if not self.service or not self.app:
            return

        # サービス経由でSyncマーカーを記録
        self.service.sync()

    def on_experiment_history_selected(self, experiment_id: str):
        """実験履歴が選択されたときの処理"""
        logger.info(f"履歴実験 '{experiment_id}' が選択されました。")

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
        logger.info(f"履歴データ '{experiment_id}' をプロットしました。")

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
def create_controller(experiment_classes: list[type[BaseExperiment]]) -> ExperimentController:
    """コントローラーのファクトリー関数"""
    controller = ExperimentController(experiment_classes)
    controller.initialize()
    return controller


# コンビニエンス関数
def launch_gui(experiment_classes: list[type[BaseExperiment]]):
    """GUIアプリケーションを起動"""
    controller = create_controller(experiment_classes)

    try:
        controller.run()
    finally:
        controller.cleanup()
