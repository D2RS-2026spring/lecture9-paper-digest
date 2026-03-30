"""缓存模块 - 管理 LLM 响应缓存"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """缓存条目"""
    cache_key: str
    pdf_hash: str
    prompt_hash: str
    model: str
    research_question: str
    method: str
    key_findings: list
    raw_response: str
    created_at: str


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self._index = self._load_index()

    def _load_index(self) -> Dict[str, str]:
        """加载缓存索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_index(self):
        """保存缓存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def _get_cache_file(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, cache_key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        if cache_key not in self._index:
            return None

        cache_file = self._get_cache_file(cache_key)
        if not cache_file.exists():
            # 缓存文件丢失，清理索引
            del self._index[cache_key]
            self._save_index()
            return None

        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return CacheEntry(**data)

    def set(self, entry: CacheEntry):
        """设置缓存条目"""
        cache_file = self._get_cache_file(entry.cache_key)

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(entry), f, ensure_ascii=False, indent=2)

        self._index[entry.cache_key] = str(cache_file)
        self._save_index()

    def invalidate(self, cache_key: str):
        """使缓存失效"""
        if cache_key in self._index:
            cache_file = self._get_cache_file(cache_key)
            if cache_file.exists():
                cache_file.unlink()
            del self._index[cache_key]
            self._save_index()

    def clear(self):
        """清空所有缓存"""
        for cache_key in list(self._index.keys()):
            self.invalidate(cache_key)

    def compute_cache_key(self, pdf_path: str, prompt: str, model: str) -> str:
        """计算缓存 key"""
        pdf_hash = compute_file_hash(pdf_path)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
        return f"{pdf_hash}_{prompt_hash}_{model}"

    def compute_file_hash(self, file_path: str) -> str:
        """计算文件 hash"""
        hash_obj = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()


def compute_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """计算文件 hash"""
    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()
