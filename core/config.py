"""配置管理模块。从 YAML 加载配置，支持嵌套路径访问和继承机制。"""

import os
import yaml
from typing import Any


class Config:
    """从 YAML 文件加载实验配置。

    支持:
    - 嵌套键路径访问 (如 "devices.vis_rotator.serial")
    - extends 继承机制 (子配置可继承父配置)
    - 默认值回退

    Usage:
        config = Config("configs/experiments/sfg_example.yaml")
        serial = config.get("devices.vis_rotator.serial")  # "55358884"
    """

    def __init__(self, config_path: str, base_dir: str = None):
        """加载 YAML 配置文件。

        Args:
            config_path: 配置文件路径（相对于 base_dir 或绝对路径）
            base_dir: 基础目录。默认自动检测为 CommandMode 目录。
        """
        self._config_path = config_path
        self._data: dict = {}

        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        full_path = os.path.join(base_dir, config_path) if not os.path.isabs(config_path) else config_path
        full_path = os.path.normpath(full_path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"配置文件不存在: {full_path}")

        self._load_file(full_path)

    def _load_file(self, filepath: str):
        """加载文件并处理 extends 继承。

        配置文件可声明 `extends: "../defaults.yaml"` 来继承父配置。
        子配置中的值会覆盖父配置中的同名键（深度合并）。
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if data.get("extends"):
            parent_path = data.pop("extends")
            parent_full = os.path.join(os.path.dirname(filepath), parent_path)
            parent_full = os.path.normpath(parent_full)
            if os.path.exists(parent_full):
                with open(parent_full, "r", encoding="utf-8") as f:
                    parent_data = yaml.safe_load(f) or {}
                self._deep_merge(parent_data, data)
                self._data = parent_data
            else:
                self._data = data
        else:
            self._data = data

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """深度合并两个字典，override 覆盖 base 中的值。

        嵌套字典递归合并，其余键直接覆盖。
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """通过点号分隔的路径获取配置值。

        Args:
            key_path: 配置路径，如 "devices.vis_rotator.serial"
            default: 键不存在时的默认值

        Returns:
            配置值，或 default
        """
        keys = key_path.split(".")
        node = self._data
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def get_devices(self) -> dict:
        """获取设备配置字典。"""
        return self._data.get("devices", {})

    def get_experiment(self) -> dict:
        """获取实验配置字典。"""
        return self._data.get("experiment", {})

    def get_output(self) -> dict:
        """获取输出配置字典。"""
        return self._data.get("output", {})

    def get_scan(self) -> dict:
        """获取扫描配置字典。"""
        return self._data.get("scan", {})

    def get_polarization(self) -> dict:
        """获取偏振配置字典。"""
        return self._data.get("polarization", {})

    def get_spectrometer(self) -> dict:
        """获取光谱仪配置字典。"""
        return self._data.get("spectrometer", {})

    def to_dict(self) -> dict:
        """返回完整配置字典的副本。"""
        return dict(self._data)

    def __repr__(self) -> str:
        return f"Config({self._config_path})"
