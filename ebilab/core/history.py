"""
管理過去の実験データの読み込みと管理
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any

import pandas as pd

from .settings import get_settings

logger = getLogger(__name__)


@dataclass
class ExperimentHistory:
    """実験履歴を表すデータクラス"""

    id: str  # ファイル名（拡張子なし）
    name: str  # 実験名
    timestamp: datetime.datetime  # 実験開始時刻
    csv_path: Path  # CSVファイルのパス
    metadata_path: Path | None = None  # メタデータファイルのパス（存在する場合）
    comment: str = ""  # コメント（将来的な実装用）

    @property
    def timestamp_str(self) -> str:
        """タイムスタンプを文字列形式で取得"""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def load_data(self) -> tuple[pd.DataFrame | None, dict[str, Any] | None]:
        """CSVデータとメタデータを読み込む"""
        try:
            # CSVファイルを読み込む
            if not self.csv_path.exists():
                logger.error(f"CSVファイルが見つかりません: {self.csv_path}")
                return None, None

            df = pd.read_csv(self.csv_path)
            logger.info(f"CSVファイルを読み込みました: {self.csv_path}")

            # メタデータファイルを読み込む（存在する場合）
            metadata = None
            if self.metadata_path and self.metadata_path.exists():
                try:
                    with open(self.metadata_path, encoding="utf-8") as f:
                        metadata = json.load(f)
                    logger.info(f"メタデータを読み込みました: {self.metadata_path}")
                except Exception as e:
                    logger.warning(f"メタデータの読み込みに失敗しました: {e}")

            return df, metadata

        except Exception as e:
            logger.error(f"実験データの読み込み中にエラーが発生しました: {e}")
            return None, None


class ExperimentHistoryManager:
    """過去の実験データの読み込みと管理を行うクラス"""

    def __init__(self):
        self.settings = get_settings()
        self.data_dir = self.settings.data.csv_base_dir
        # experiment_id -> ExperimentHistory のキャッシュ
        self._history_cache: dict[str, ExperimentHistory] = {}

    def get_experiment_history(self) -> list[ExperimentHistory]:
        """実験履歴の一覧を取得"""
        if not self.data_dir.exists():
            logger.warning(f"データディレクトリが存在しません: {self.data_dir}")
            return []

        history_items = []

        try:
            for date_folder in sorted(self.data_dir.iterdir(), reverse=True):
                if not date_folder.is_dir():
                    continue

                # CSVファイルを探す
                for csv_file in sorted(date_folder.glob("*.csv"), reverse=True):
                    # ファイル名からメタデータを抽出
                    filename = csv_file.stem  # 拡張子を除いたファイル名
                    parts = filename.split("-")

                    if len(parts) >= 3:
                        try:
                            # メタデータファイルのパスを確認
                            metadata_path = csv_file.with_suffix(".json")
                            if not metadata_path.exists():
                                # メタデータがない場合はスキップ
                                logger.debug(
                                    f"メタデータファイルが存在しないためスキップ: {metadata_path}"
                                )
                                continue

                            # メタデータを読み込む
                            with open(metadata_path, encoding="utf-8") as f:
                                metadata = json.load(f)

                            # 必須フィールドを取得（KeyErrorの場合はスキップ）
                            experiment_name = metadata["experiment_name"]
                            timestamp = datetime.datetime.fromisoformat(metadata["start_time"])

                            # コメントを取得（存在しない場合は空文字列）
                            comment = metadata.get("comment", "")

                            # ExperimentHistoryオブジェクトを作成
                            history = ExperimentHistory(
                                id=filename,
                                name=experiment_name,
                                timestamp=timestamp,
                                csv_path=csv_file,
                                metadata_path=metadata_path,
                                comment=comment,
                            )

                            # キャッシュに保存
                            self._history_cache[filename] = history
                            history_items.append(history)

                        except (ValueError, json.JSONDecodeError, KeyError) as e:
                            logger.warning(
                                f"メタデータの読み込みまたは解析に失敗しました: {filename}, {e}"
                            )

            logger.info(f"実験履歴を{len(history_items)}件読み込みました。")
            return history_items

        except Exception as e:
            logger.error(f"実験履歴の読み込み中にエラーが発生しました: {e}")
            return []

    def load_experiment_data(
        self, experiment_id: str
    ) -> tuple[pd.DataFrame | None, dict[str, Any] | None]:
        """
        指定された実験IDのデータを読み込む

        Note: このメソッドはキャッシュからのみデータを取得します。
              事前にget_experiment_history()を呼び出してキャッシュを構築する必要があります。

        Returns:
            tuple: (DataFrame, metadata dict) or (None, None) if error
        """
        # キャッシュから取得
        if experiment_id in self._history_cache:
            history = self._history_cache[experiment_id]
            return history.load_data()

        # キャッシュにない場合はエラー
        logger.error(f"実験履歴がキャッシュに見つかりません: {experiment_id}")
        logger.error("get_experiment_history()を呼び出してキャッシュを更新してください。")
        return None, None

    def get_experiment_name_from_id(self, experiment_id: str) -> str | None:
        """実験IDから実験名を取得"""
        parts = experiment_id.split("-")
        if len(parts) >= 3:
            return "-".join(parts[:-2])
        return None

    def refresh_cache(self):
        """キャッシュをクリアして再読み込みを促す"""
        self._history_cache.clear()
        logger.info("実験履歴のキャッシュをクリアしました。")

    def update_comment(self, experiment_id: str, comment: str) -> bool:
        """
        指定された実験のコメントを更新する

        Args:
            experiment_id: 実験ID（ファイル名）
            comment: 新しいコメント

        Returns:
            bool: 更新成功の場合True、失敗の場合False
        """
        # キャッシュから実験履歴を取得
        if experiment_id not in self._history_cache:
            logger.error(f"実験履歴がキャッシュに見つかりません: {experiment_id}")
            return False

        history = self._history_cache[experiment_id]

        # メタデータファイルがない場合はエラー
        if not history.metadata_path or not history.metadata_path.exists():
            logger.error(f"メタデータファイルが存在しません: {history.metadata_path}")
            return False

        try:
            # 既存のメタデータを読み込む
            with open(history.metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

            # コメントを更新
            metadata["comment"] = comment

            # メタデータファイルに書き込む
            with open(history.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # キャッシュも更新
            history.comment = comment

            logger.info(f"コメントを更新しました: {experiment_id}")
            return True

        except Exception as e:
            logger.error(f"コメントの更新中にエラーが発生しました: {e}")
            return False
