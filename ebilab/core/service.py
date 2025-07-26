# src/ebilab/services/application.py

import asyncio
import threading
from enum import Enum, auto
from typing import Type, Dict, Any
from logging import getLogger

from ..api.experiment import BaseExperiment
from .event import Event

logger = getLogger(__name__)

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
        self.current_experiment_cls: Type[BaseExperiment] = None
        self.status = ExperimentStatus.IDLE
        self.data_queue = None
        self.stop_event = None
        self._worker_task = None
        
        # 実験ごとのリソース管理（実験開始時に作成）
        self.loop: asyncio.AbstractEventLoop = None
        self.loop_thread: threading.Thread = None
        self._experiment_active = False
        
        # ステータス変更コールバック
        self._status_callbacks = []

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
        if self.status == ExperimentStatus.RUNNING and self.loop:
            asyncio.run_coroutine_threadsafe(self.stop_experiment(), self.loop)
            
        self._stop_experiment_thread()

    def get_status(self) -> ExperimentStatus:
        """現在の実験ステータスを取得"""
        return self.status

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
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def _set_status(self, status: ExperimentStatus):
        """ステータスを設定し、コールバックに通知"""
        if self.status != status:
            self.status = status
            self._notify_status_change()

    def start_experiment(self, experiment_cls: Type[BaseExperiment], params: Dict[str, Any]):
        """
        新しい実験を開始する。

        Args:
            experiment_cls: 実行する実験クラス
            params: Experimentのフィールドに渡すパラメータの辞書。
        """
        if self.status == ExperimentStatus.RUNNING:
            logger.warning("Experiment is already running.")
            return

        # 実験専用スレッドを開始
        if not self._start_experiment_thread():
            logger.error("Failed to start experiment thread")
            return

        logger.info("Service: Starting experiment...")
        self.current_experiment_cls = experiment_cls
        self._set_status(ExperimentStatus.RUNNING)

        # 新しいキューとイベントを作成（実験ごとに新規作成）
        self.data_queue = asyncio.Queue()
        self.stop_event = asyncio.Event()

        experiment_instance = experiment_cls(params)

        
        # スレッドが完全に起動するまで少し待つ
        import time
        time.sleep(0.1)

        # 非同期タスクとして実験のライフサイクルを実行
        # self._worker_task = asyncio.create_task()
        asyncio.run_coroutine_threadsafe(
            self._run_lifecycle(experiment_instance),
            # self.start_experiment(experiment_cls, params), 
            self.loop,
        )

    # def start_experiment_sync(self, experiment_cls: Type[BaseExperiment], params: Dict[str, Any]):
    #     """
    #     同期的に実験を開始する（UIスレッドから呼び出し用）
    #     実験ごとに新しいスレッドを作成する
    #     """
    #     if self.status == ExperimentStatus.RUNNING:
    #         logger.warning("Experiment is already running.")
    #         return

    #     # 実験専用スレッドを開始
    #     if not self._start_experiment_thread():
    #         logger.error("Failed to start experiment thread")
    #         return

    #     # スレッドが完全に起動するまで少し待つ
    #     import time
    #     time.sleep(0.1)
            
    #     asyncio.run_coroutine_threadsafe(
    #         self.start_experiment(experiment_cls, params), 
    #         self.loop
    #     )

    async def stop_experiment(self):
        """実行中の実験を中断する。"""
        if self.status != ExperimentStatus.RUNNING:
            return

        logger.info("Service: Stopping experiment...")
        self._set_status(ExperimentStatus.STOPPING)
        self.stop_event.set()
        if self._worker_task:
            await self._worker_task
            
        # 実験終了後にスレッドも停止
        self._stop_experiment_thread()

    def stop_experiment_sync(self):
        """
        同期的に実験を停止する（UIスレッドから呼び出し用）
        """
        if not self.loop or not self._experiment_active:
            logger.error("No active experiment to stop.")
            return
            
        asyncio.run_coroutine_threadsafe(self.stop_experiment(), self.loop)

    async def get_data_stream(self):
        """実験データをリアルタイムで取得するための非同期ジェネレータ。"""
        while self.status == ExperimentStatus.RUNNING or not self.data_queue.empty():
            try:
                # タイムアウト付きで待機し、定期的にステータスをチェック
                data = await asyncio.wait_for(self.data_queue.get(), timeout=0.1)
                yield data
                self.data_queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def _run_lifecycle(self, exp: BaseExperiment):
        """実験のsetup -> steps -> cleanupのライフサイクルを管理する内部メソッド。"""

        logger.debug(f"Starting lifecycle for {exp.name} with parameters: {exp._options}")
        import time

        try:
            await exp.setup()
            start_time = time.perf_counter()

            async for data in exp.steps():
                if self.stop_event.is_set():
                    logger.info("Service: Stop detected, breaking steps loop.")
                    break

                # タイムスタンプを追加
                if isinstance(data, dict):
                    data = data.copy()  # 元のデータを変更しないようにコピー
                    current_time = time.perf_counter()
                    data["t"] = current_time - start_time  # 実験開始からの経過時間
                    if "time" not in data:
                        data["time"] = current_time  # 絶対時間

                # ここでファイルへのデータ保存処理などを挟むことができる
                # TODO: Save data to file
                # self.save_to_file(data)

                await self.data_queue.put(data)

        except Exception as e:
            logger.error(f"Error during experiment execution: {e}")
            self._set_status(ExperimentStatus.ERROR)
        finally:
            logger.info("Service: Executing cleanup...")
            await exp.cleanup()
            if self.status != ExperimentStatus.ERROR:
                self._set_status(ExperimentStatus.FINISHED)

            # ワーカースレッドの終了を通知
            self._worker_task = None
            logger.info(f"Service: Lifecycle finished with status {self.status.name}.")
            
            # 実験終了後にスレッドを停止
            logger.info("Service: Scheduling thread shutdown after experiment completion...")
            asyncio.create_task(self._shutdown_after_delay())

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
