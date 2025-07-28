"""
Settings management for ebilab.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel, Field

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("tomli is required for Python < 3.11. Install with: pip install tomli")


# @dataclass
class DataSettings(BaseModel):
    # CSV保存先のベースディレクトリ
    csv_base_dir: Path = Field(default_factory=lambda: Path("data"))

    # ファイル名のフォーマット
    filename_format: str = "{name}-{timestamp}"

    # タイムスタンプのフォーマット
    timestamp_format: str = "%Y%m%d-%H%M%S"

    # 日付ごとのサブフォルダを作成するか
    use_date_subfolder: bool = True

    # 日付フォルダのフォーマット
    date_folder_format: str = "%y%m%d"


# @dataclass
class Settings(BaseModel):
    data: DataSettings = Field(default_factory=DataSettings)


class SettingsManager:
    """設定の読み込み・保存を管理するクラス"""

    def __init__(self, config_file: Path | None = None):
        self.config_file = config_file or self._find_config_file()
        self._load_settings()

    def _find_config_file(self) -> Path | None:
        """設定ファイルを検索"""
        # 現在のディレクトリから上位に向かってpyproject.tomlを探す
        current = Path.cwd()
        for path in [current] + list(current.parents):
            config_file = path / "pyproject.toml"
            if config_file.exists():
                return config_file
        return None

    def _load_settings(self):
        """Load config file from pyproject.toml"""
        if not self.config_file or not self.config_file.exists():
            return

        try:
            with open(self.config_file, "rb") as f:
                config = tomllib.load(f)
        except Exception:
            return

        config_dict = config.get("tool", {}).get("ebilab", {})
        self._settings = Settings.model_validate(config_dict)

    def get_settings(self) -> Settings:
        return self._settings


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
