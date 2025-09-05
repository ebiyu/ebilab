"""
Data saving functionality for experiments.
"""

from __future__ import annotations

import csv
import datetime
import json
import logging
from logging import FileHandler, Formatter, getLogger
from pathlib import Path
from typing import Any, TextIO

from .settings import get_settings

logger = getLogger(__name__)


class ExperimentLoggerManager:
    """Manages logging for experiments, including file handlers and paths."""

    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.file_handler: FileHandler | None = None
        self.file_handler_debug: FileHandler | None = None
        self.log_path: Path | None = None
        self.log_path_debug: Path | None = None
        self.experiment_logger = getLogger(f"ebilab.experiment.{experiment_name}")

        self._initialize()

    def _initialize(self):
        """Create a file handler for logging."""
        settings = get_settings()
        data_settings = settings.data

        # Create directory if it doesn't exist
        save_dir = data_settings.csv_base_dir / datetime.datetime.now().strftime(
            data_settings.date_folder_format
        )
        save_dir.mkdir(parents=True, exist_ok=True)

        # Create log file path
        timestamp = datetime.datetime.now().strftime(data_settings.timestamp_format)
        filename = data_settings.filename_format.format(
            name=self.experiment_name, timestamp=timestamp
        )
        self.log_path = save_dir / f"{filename}.log"
        self.log_path_debug = save_dir / f"{filename}.debug.log"

        # Create file handler
        formatter = Formatter("%(asctime)s - %(levelname)s - %(message)s")

        self.file_handler = FileHandler(self.log_path, mode="w", encoding="utf-8")
        self.file_handler.setLevel(logging.INFO)
        self.file_handler.setFormatter(formatter)

        self.file_handler_debug = FileHandler(self.log_path_debug, mode="w", encoding="utf-8")
        self.file_handler_debug.setLevel(logging.DEBUG)
        self.file_handler_debug.setFormatter(formatter)

        # self.experiment

        self.experiment_logger.addHandler(self.file_handler)
        self.experiment_logger.addHandler(self.file_handler_debug)

        logger.debug(f"Created experiment log handler: {self.log_path}")
        logger.debug(f"Created experiment debug log handler: {self.log_path_debug}")

    def cleanup(self):
        """Clean up file handlers and close log files."""
        if self.file_handler:
            self.experiment_logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None
            logger.debug(f"Closed experiment log handler: {self.log_path}")

        if self.file_handler_debug:
            self.experiment_logger.removeHandler(self.file_handler_debug)
            self.file_handler_debug.close()
            self.file_handler_debug = None
            logger.debug(f"Closed experiment debug log handler: {self.log_path_debug}")


class ExperimentDataSaver:
    """実験データをCSVファイルに保存するクラス"""

    def __init__(self, experiment_name: str, columns: list[str]):
        self.experiment_name = experiment_name
        self.columns = columns
        self.csv_file: TextIO | None = None
        self.csv_writer: csv.writer | None = None
        self.csv_path: Path | None = None

        # 保存先パスを決定
        self._prepare_save_path()

    def _prepare_save_path(self):
        """保存先パスを準備"""
        settings = get_settings()
        data_settings = settings.data

        # ベースディレクトリ
        base_dir = data_settings.csv_base_dir

        # 日付フォルダを使用する場合
        if data_settings.use_date_subfolder:
            date_str = datetime.datetime.now().strftime(data_settings.date_folder_format)
            save_dir = base_dir / date_str
        else:
            save_dir = base_dir

        # ディレクトリを作成
        save_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名を生成
        timestamp = datetime.datetime.now().strftime(data_settings.timestamp_format)
        filename = data_settings.filename_format.format(
            name=self.experiment_name, timestamp=timestamp
        )

        self.csv_path = save_dir / f"{filename}.csv"
        self.metadata_path = save_dir / f"{filename}.json"
        logger.info(f"Data will be saved to: {self.csv_path}")

    def save_metadata(
        self,
        experiment_class_name: str,
        parameters: dict[str, Any],
        plotter_names: list[str] | None = None,
    ):
        """実験のメタデータをJSONファイルに保存"""
        metadata = {
            "experiment_name": self.experiment_name,
            "experiment_class": experiment_class_name,
            "parameters": parameters,
            "plotters": plotter_names or [],
            "start_time": datetime.datetime.now().isoformat(),
            "columns": self.columns,
            "csv_file": self.csv_path.name,
        }

        try:
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Metadata saved to: {self.metadata_path}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def start_writing(self):
        """CSVファイルの書き込みを開始"""
        if self.csv_file is not None:
            logger.warning("CSV file is already open")
            return

        try:
            self.csv_file = open(self.csv_path, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)

            # ヘッダー行を書き込み（時間カラムを自動追加）
            headers = ["t", "sync_t", "time"] + self.columns
            self.csv_writer.writerow(headers)

            # すぐにフラッシュして確実に書き込み
            self.csv_file.flush()

            logger.info(f"Started writing CSV to: {self.csv_path}")

        except Exception as e:
            logger.error(f"Failed to open CSV file for writing: {e}")
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            raise

    def write_data(self, data: dict[str, Any]):
        """データを1行書き込み"""
        if self.csv_writer is None:
            logger.error("CSV writer is not initialized")
            return

        try:
            # ヘッダーと同じ順序でデータを整理
            headers = ["t", "sync_t", "time"] + self.columns
            row = []

            for header in headers:
                value = data.get(header, "")  # 存在しない列は空文字
                row.append(value)

            self.csv_writer.writerow(row)
            self.csv_file.flush()  # データを確実に書き込み

        except Exception as e:
            logger.error(f"Failed to write data to CSV: {e}")

    def stop_writing(self):
        """CSVファイルの書き込みを終了"""
        if self.csv_file is not None:
            try:
                self.csv_file.close()
                logger.info(f"Closed CSV file: {self.csv_path}")
            except Exception as e:
                logger.error(f"Error closing CSV file: {e}")
            finally:
                self.csv_file = None
                self.csv_writer = None

    def get_save_path(self) -> Path | None:
        """保存先パスを取得"""
        return self.csv_path
