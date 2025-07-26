# src/ebilab/services/application.py

import asyncio
import threading
from enum import Enum, auto
from typing import Type, Dict, Any

from ..api.experiment import BaseExperiment
from .event import Event


class ExperimentStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPING = auto()
    FINISHED = auto()
    ERROR = auto()


class ExperimentService:
    """
    実験の実行、状態管理、データ保存など、UIに依存しないコアロジックを担う。
    このクラスはシングルトンとして、または依存性注入によってアプリケーション全体で
    単一のインスタンスが使われることを想定しています。
    """

    def __init__(self, experiment_cls: Type[BaseExperiment]):
        self.experiment_cls = experiment_cls
        self.status = ExperimentStatus.IDLE
        self.data_queue = asyncio.Queue()
        self.stop_event = asyncio.Event()
        self._worker_task = None

    async def start_experiment(self, params: Dict[str, Any]):
        """
        新しい実験を開始する。

        Args:
            params: Experimentのフィールドに渡すパラメータの辞書。
        """
        if self.status == ExperimentStatus.RUNNING:
            print("Warning: Experiment is already running.")
            return

        print("Service: Starting experiment...")
        self.status = ExperimentStatus.RUNNING
        self.stop_event.clear()

        experiment_instance = self.experiment_cls(**params)

        # 非同期タスクとして実験のライフサイクルを実行
        self._worker_task = asyncio.create_task(self._run_lifecycle(experiment_instance))

    async def stop_experiment(self):
        """実行中の実験を中断する。"""
        if self.status != ExperimentStatus.RUNNING:
            return

        print("Service: Stopping experiment...")
        self.status = ExperimentStatus.STOPPING
        self.stop_event.set()
        if self._worker_task:
            await self._worker_task

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
        import time

        try:
            await exp.setup()
            start_time = time.perf_counter()

            async for data in exp.steps():
                if self.stop_event.is_set():
                    print("Service: Stop detected, breaking steps loop.")
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
            print(f"Error during experiment execution: {e}")
            self.status = ExperimentStatus.ERROR
        finally:
            print("Service: Executing cleanup...")
            await exp.cleanup()
            if self.status != ExperimentStatus.ERROR:
                self.status = ExperimentStatus.FINISHED

            # ワーカースレッドの終了を通知
            self._worker_task = None
            print(f"Service: Lifecycle finished with status {self.status.name}.")
