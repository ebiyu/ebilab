"""
Settings management for ebilab.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DataSettings:
    """データ保存に関する設定"""

    # CSV保存先のベースディレクトリ
    csv_base_dir: Path = field(default_factory=lambda: Path("data"))

    # ファイル名のフォーマット
    filename_format: str = "{name}-{timestamp}"

    # タイムスタンプのフォーマット
    timestamp_format: str = "%Y%m%d-%H%M%S"

    # 日付ごとのサブフォルダを作成するか
    use_date_subfolder: bool = True

    # 日付フォルダのフォーマット
    date_folder_format: str = "%y%m%d"


@dataclass
class Settings:
    """アプリケーション全体の設定"""

    data: DataSettings = field(default_factory=DataSettings)


class SettingsManager:
    """設定の読み込み・保存を管理するクラス"""

    def __init__(self, config_file: Path | None = None):
        self.config_file = config_file or self._find_config_file()
        self._settings = Settings()
        self._load_settings()

    def _find_config_file(self) -> Path | None:
        """設定ファイルを検索"""
        # 現在のディレクトリから上位に向かってebilab.iniを探す
        current = Path.cwd()
        for path in [current] + list(current.parents):
            config_file = path / "ebilab.ini"
            if config_file.exists():
                return config_file
        return None

    def _load_settings(self):
        """設定ファイルから設定を読み込み"""
        if not self.config_file or not self.config_file.exists():
            return

        config = configparser.ConfigParser()
        config.read(self.config_file, encoding="utf-8")

        # データ設定の読み込み
        if "data" in config:
            data_section = config["data"]

            if "csv_base_dir" in data_section:
                self._settings.data.csv_base_dir = Path(data_section["csv_base_dir"])

            if "filename_format" in data_section:
                self._settings.data.filename_format = data_section["filename_format"]

            if "timestamp_format" in data_section:
                self._settings.data.timestamp_format = data_section["timestamp_format"]

            if "use_date_subfolder" in data_section:
                self._settings.data.use_date_subfolder = data_section.getboolean(
                    "use_date_subfolder"
                )

            if "date_folder_format" in data_section:
                self._settings.data.date_folder_format = data_section["date_folder_format"]

    def get_settings(self) -> Settings:
        """設定を取得"""
        return self._settings

    def update_csv_base_dir(self, new_dir: Path):
        """CSV保存先を更新"""
        self._settings.data.csv_base_dir = new_dir

    def save_settings(self):
        """設定をファイルに保存"""
        if not self.config_file:
            self.config_file = Path.cwd() / "ebilab.ini"

        config = configparser.ConfigParser()

        # データ設定の保存
        config["data"] = {
            "csv_base_dir": str(self._settings.data.csv_base_dir),
            "filename_format": self._settings.data.filename_format,
            "timestamp_format": self._settings.data.timestamp_format,
            "use_date_subfolder": str(self._settings.data.use_date_subfolder),
            "date_folder_format": self._settings.data.date_folder_format,
        }

        with open(self.config_file, "w", encoding="utf-8") as f:
            config.write(f)


# グローバル設定管理インスタンス
_settings_manager: SettingsManager | None = None


def get_settings_manager() -> SettingsManager:
    """設定管理インスタンスを取得"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def get_settings() -> Settings:
    """アプリケーション設定を取得"""
    return get_settings_manager().get_settings()
