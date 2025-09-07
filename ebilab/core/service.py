# src/ebilab/services/application.py
from __future__ import annotations

import asyncio
import datetime
import queue
import threading
import time
from enum import Enum, auto
from logging import getLogger
from typing import Any

from ..api.experiment import BaseExperiment
from .data_saver import ExperimentDataSaver, ExperimentLoggerManager

logger = getLogger(__name__)


class ExperimentStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPING = auto()
    FINISHED = auto()
    ERROR = auto()


class ExperimentService:
    """
    実験の実行、状態管理、データ保存など、UIに依存しないコアロジックを担う。
    アプリケーションの起動から終了まで存続し、スレッドやキューの管理を行う。
    """

    def __init__(self):
        self.current_experiment_cls: type[BaseExperiment] = None
        self.current_experiment_instance: BaseExperiment = None
        self.status = ExperimentStatus.IDLE
        self.data_queue = None
        self.stop_event = None
        self._worker_task = None
        self._steps_task = None  # 実験のsteps()を実行するタスク

        # 実験ごとのリソース管理（実験開始時に作成）
        self.loop: asyncio.AbstractEventLoop = None
        self.loop_thread: threading.Thread = None
        self._experiment_active = False
        self._experiment_start_time: float | None = None

        # データ保存関連
        self.data_saver: ExperimentDataSaver | None = None
        self.experiment_logger: getLogger | None = None
        self.experiment_logger_manager: ExperimentLoggerManager | None = None

        # デバッグモードフラグ
        self.debug_mode: bool = False

        # ステータス変更コールバック
        self._status_callbacks = []

        # sync時刻の管理
        self._last_sync_time: float | None = None

        # エラー情報（最後に発生したエラー）
        self._last_error: Exception | None = None

    def initialize(self):
        """サービスの初期化（軽量な初期化のみ）"""
        logger.info("Service: Service initialized (per-experiment threading mode)")

    def shutdown(self):
        """サービスのシャットダウン"""
        logger.info("Service: Shutting down...")

        # 実行中の実験があれば停止
        if self._experiment_active:
            self._stop_current_experiment()

    def _start_experiment_thread(self):
        """実験専用のイベントループとスレッドを作成"""
        if self._experiment_active:
            logger.warning("Experiment thread already active")
            return False

        logger.info("Service: Starting experiment thread...")

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        self._experiment_active = True
        return True

    def _stop_experiment_thread(self):
        """実験専用のイベントループとスレッドを停止"""
        if not self._experiment_active:
            return

        logger.info("Service: Stopping experiment thread...")

        # イベントループを停止
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

        if self.loop_thread:
            self.loop_thread.join(timeout=2.0)

        self.loop = None
        self.loop_thread = None
        self._experiment_active = False

    def _stop_current_experiment(self):
        """現在の実験を強制停止"""
        if self.status == ExperimentStatus.RUNNING:
            # threading.Eventを直接使用（マルチスレッドセーフ）
            self.stop_experiment()

        self._stop_experiment_thread()

    def get_status(self) -> ExperimentStatus:
        """現在の実験ステータスを取得"""
        return self.status

    def get_last_error(self) -> Exception | None:
        """最後に発生したエラーを取得"""
        return self._last_error

    def get_current_experiment_instance(self) -> BaseExperiment | None:
        """現在実行中の実験インスタンスを取得"""
        return self.current_experiment_instance

    def is_running(self) -> bool:
        """実験が実行中かどうかを判定"""
        return self.status == ExperimentStatus.RUNNING

    def add_status_callback(self, callback):
        """ステータス変更時に呼び出されるコールバックを追加"""
        self._status_callbacks.append(callback)

    def _notify_status_change(self):
        """ステータス変更をコールバックに通知"""
        for callback in self._status_callbacks:
            try:
                callback(self.status)
            except Exception:
                logger.exception("Status callback failed")

    def _set_status(self, status: ExperimentStatus):
        """ステータスを設定し、コールバックに通知"""
        if self.status != status:
            self.status = status
            self._notify_status_change()

    def start_experiment(
        self, experiment_cls: type[BaseExperiment], params: dict[str, Any], debug_mode: bool = False
    ):
        """
        新しい実験を開始する。

        Args:
            experiment_cls: 実行する実験クラス
            params: Experimentのフィールドに渡すパラメータの辞書。
            debug_mode: デバッグモードで実行するかどうか
        """
        self.debug_mode = debug_mode
        if self.status == ExperimentStatus.RUNNING:
            logger.warning("Experiment is already running.")
            return

        # 実験専用スレッドを開始
        if not self._start_experiment_thread():
            logger.error("Failed to start experiment thread")
            return

        logger.info("Service: Starting experiment...")
        self.current_experiment_cls = experiment_cls
        # 前回のエラー情報をクリア
        self._last_error = None
        self._set_status(ExperimentStatus.RUNNING)

        # 新しいキューとイベントを作成（実験ごとに新規作成）
        self.data_queue = queue.Queue()  # マルチスレッドセーフなqueue.Queueを使用
        self.stop_event = threading.Event()  # マルチスレッドセーフなthreading.Eventを使用

        experiment_instance = experiment_cls(params)
        self.current_experiment_instance = experiment_instance

        # デバッグモードでない場合のみデータ保存の準備
        if not self.debug_mode:
            self._setup_data_saving(experiment_instance)
        else:
            logger.info("Data saving is disabled in debug mode")
            self.data_saver = None

        # 実験ロガーのセットアップ
        self._setup_experiment_logging(experiment_instance)

        # Wait for the thread to fully start
        time.sleep(0.1)

        # 非同期タスクとして実験のライフサイクルを実行
        asyncio.run_coroutine_threadsafe(
            self._run_lifecycle(experiment_instance),
            self.loop,
        )

    def _setup_data_saving(self, experiment_instance: BaseExperiment):
        """データ保存の初期化"""
        # CSV保存の準備
        self.data_saver = ExperimentDataSaver(
            experiment_name=experiment_instance.name, columns=experiment_instance.columns
        )
        self.data_saver.start_writing()

        # メタデータを保存
        plotter_names = []
        if hasattr(experiment_instance.__class__, "_plotters"):
            plotter_names = [p.name for p in experiment_instance.__class__._plotters]

        self.data_saver.save_metadata(
            experiment_class_name=experiment_instance.__class__.__name__,
            parameters=experiment_instance._options,
            plotter_names=plotter_names,
        )

        logger.info("Data saving initialized successfully")

    def _setup_experiment_logging(self, experiment_instance: BaseExperiment):
        """実験ロガーのセットアップ"""
        if not self.debug_mode:
            # Create a logger and file handler for the experiment
            self.experiment_logger_manager = ExperimentLoggerManager(experiment_instance.name)
            self.experiment_logger = self.experiment_logger_manager.experiment_logger
            logger.info(
                f"Experiment logging setup complete: {self.experiment_logger_manager.log_path}, "
                f"{self.experiment_logger_manager.log_path_debug}"
            )
        else:
            # Debug mode: create logger without file handlers
            from logging import getLogger

            self.experiment_logger = getLogger(f"ebilab.experiment.{experiment_instance.name}")
            self.experiment_logger_manager = None
            logger.info("Experiment logging disabled in debug mode")

        # inject logger into the experiment instance
        experiment_instance.logger = self.experiment_logger

    def stop_experiment(self):
        """実行中の実験を中断する。"""
        if self.status != ExperimentStatus.RUNNING:
            return

        logger.info("Service: Stopping experiment...")
        self._set_status(ExperimentStatus.STOPPING)
        self.stop_event.set()

        # steps()タスクをキャンセル
        if self._steps_task and not self._steps_task.done():
            logger.info("Service: Cancelling steps task...")
            self.loop.call_soon_threadsafe(self._steps_task.cancel)

    def sync(self):
        """Syncマーカーを記録する。"""
        if self.status != ExperimentStatus.RUNNING:
            logger.warning("Cannot sync: experiment is not running")
            return

        # 現在の時刻とtを計算してキューに送信
        current_time = time.perf_counter()
        if hasattr(self, "_experiment_start_time") and self._experiment_start_time:
            t = current_time - self._experiment_start_time
        else:
            t = 0.0

        # sync時刻を更新
        self._last_sync_time = current_time

        # record log
        if self.experiment_logger:
            self.experiment_logger.info(f"[sync] Sync marker at t={t:.3f}s")

        logger.info(f"Service: Sync marker recorded at t={t:.3f}s")

    async def _run_steps(self, exp: BaseExperiment, start_time: float):
        """実験のsteps()を実行し、データを処理する"""
        async for data in exp.steps():
            # Check if the stop event is set
            if self.stop_event.is_set():
                logger.info("Service: Stop detected, breaking steps loop.")
                break

            # Save data to queue
            if isinstance(data, dict):
                data = data.copy()
                current_time = time.perf_counter()
                data["t"] = current_time - start_time
                data["sync_t"] = current_time - self._last_sync_time if self._last_sync_time else -1
                data["time"] = datetime.datetime.now().isoformat()

            # Save data to file
            # デバッグモードでない場合のみデータ保存
            if not self.debug_mode:
                if not self.data_saver:
                    logger.error("Data saver is not initialized")
                    raise RuntimeError("Data saver is not initialized")

                try:
                    self.data_saver.write_data(data)
                except Exception:
                    logger.exception("Failed to save data to file")
                    raise

            # Add to queue (Send to UI)
            self.data_queue.put(data)

    async def _run_lifecycle(self, exp: BaseExperiment):
        """実験のsetup -> steps -> cleanupのライフサイクルを管理する内部メソッド。"""

        logger.debug(f"Starting lifecycle for {exp.name} with parameters: {exp._options}")

        try:
            exp.logger.info(f"[system] Starting experiment: {exp.name}")
            start_time = time.perf_counter()
            self._experiment_start_time = start_time  # 開始時刻を記録
            self._last_sync_time = None  # 最初のsyncまではNone
            await exp.setup()
            exp.logger.info(
                f"[system] Setup complete for experiment: {exp.name}, "
                f"took {time.perf_counter() - start_time:.2f} seconds."
            )
            exp.logger.info("[system] Running steps...")

            # steps()をタスクとして実行
            self._steps_task = asyncio.create_task(self._run_steps(exp, start_time))
            await self._steps_task

        except asyncio.CancelledError:
            logger.info("Service: Experiment was cancelled")
            exp.logger.info("[system] Experiment was cancelled by user")
            # キャンセルは正常な中断として扱う
        except Exception as e:
            logger.exception("Error during experiment execution")
            exp.logger.exception("[system] Error during experiment execution")
            # エラーを保存
            self._last_error = e
            self._set_status(ExperimentStatus.ERROR)
        finally:
            logger.info("Service: Executing cleanup...")
            exp.logger.info("[system] Experiment finished. Cleaning up...")
            await exp.cleanup()
            exp.logger.info(f"[system] cleanup() complete for experiment: {exp.name}")

            # データ保存のクリーンアップ
            self._cleanup_data_saving()

            if self.status != ExperimentStatus.ERROR:
                self._set_status(ExperimentStatus.FINISHED)

            # 実験インスタンスをクリア
            self.current_experiment_instance = None

            # ワーカースレッドの終了を通知
            self._worker_task = None
            logger.info(f"Service: Lifecycle finished with status {self.status.name}.")

            # Stop the experiment thread
            logger.info("Service: Scheduling thread shutdown after experiment completion...")
            asyncio.create_task(self._shutdown_after_delay())

    def _cleanup_data_saving(self):
        """データ保存のクリーンアップ"""
        if self.data_saver:
            self.data_saver.stop_writing()
            logger.info(f"CSV saved to: {self.data_saver.get_save_path()}")
            self.data_saver = None

        # 実験ロガーのクリーンアップ
        if hasattr(self, "experiment_logger_manager") and self.experiment_logger_manager:
            self.experiment_logger.info("Experiment completed")
            self.experiment_logger_manager.cleanup()
            self.experiment_logger_manager = None
            self.experiment_logger = None
        elif hasattr(self, "experiment_logger") and self.experiment_logger:
            # Debug mode: just clear the logger reference
            self.experiment_logger = None

    async def _shutdown_after_delay(self):
        """実験終了後、少し遅延してスレッドを停止"""
        await asyncio.sleep(0.5)  # データストリームの処理完了を待つ
        if not self._experiment_active:
            return

        logger.info("Service: Shutting down experiment thread after completion...")

        # 現在のイベントループからスレッド停止をスケジュール
        def shutdown_thread():
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)

        threading.Thread(target=shutdown_thread, daemon=True).start()

        # フラグを更新
        self._experiment_active = False
