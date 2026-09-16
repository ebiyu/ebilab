"""
Settings management for ebilab.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("tomli is required for Python < 3.11. Install with: pip install tomli")


# @dataclass
class DataSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    model_config = ConfigDict(extra="forbid")

    data: DataSettings = Field(default_factory=DataSettings)


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """overrides を base に再帰的にマージした新しい dict を返す"""
    result = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class SettingsManager:
    """設定の読み込み・保存を管理するクラス"""

    def __init__(self, config_file: Path | None = None, overrides: dict[str, Any] | None = None):
        """
        Args:
            config_file: 設定ファイル。未指定の場合は pyproject.toml を探索する。
            overrides: 設定ファイルの値を部分的に上書きする dict
                (例: ``{"data": {"csv_base_dir": "data2"}}``)。
        """
        self.config_file = config_file or self._find_config_file()
        self.overrides = overrides or {}
        self._settings = Settings()
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
        """Load config file from pyproject.toml and apply overrides"""
        self._settings = Settings.model_validate(
            _deep_merge(self._read_config_file(), self.overrides)
        )

    def _read_config_file(self) -> dict[str, Any]:
        """pyproject.toml の tool.ebilab セクションを読み込む"""
        if not self.config_file or not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, "rb") as f:
                config = tomllib.load(f)
        except Exception:
            return {}

        return config.get("tool", {}).get("ebilab", {})

    def get_settings(self) -> Settings:
        return self._settings


def load_settings(overrides: dict[str, Any] | None = None) -> Settings:
    """設定ファイルを読み込み、overrides を適用した設定を返す"""
    return SettingsManager(overrides=overrides).get_settings()
