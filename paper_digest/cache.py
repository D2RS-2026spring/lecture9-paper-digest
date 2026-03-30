"""缓存模块 - 管理 LLM 响应缓存"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


class CacheManager:
    """缓存管理器 - 存储任意格式的分析结果"""

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_file(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        cache_file = self._get_cache_file(cache_key)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 缓存文件损坏，删除
            cache_file.unlink(missing_ok=True)
            return None

    def set(self, cache_key: str, result: Dict[str, Any]):
        """设置缓存结果"""
        cache_file = self._get_cache_file(cache_key)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def invalidate(self, cache_key: str):
        """使缓存失效"""
        cache_file = self._get_cache_file(cache_key)
        if cache_file.exists():
            cache_file.unlink()

    def clear(self):
        """清空所有缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


def compute_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """计算文件 hash"""
    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()
