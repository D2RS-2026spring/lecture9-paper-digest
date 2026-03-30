"""LLM 模块 - 处理 Qwen API 调用"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from openai import OpenAI
from dotenv import load_dotenv


# 分析结果现在以字典形式返回，存储在 .cache/ 中


class QwenClient:
    """Qwen API 客户端"""

    DEFAULT_SYSTEM_PROMPT = """你是一个学术论文分析专家。请仔细阅读论文，提取以下信息并以 JSON 格式返回：

【输出格式要求】
{
  "research_question": "论文的核心研究问题，字符串类型，必需",
  "method": "论文使用的研究方法，字符串类型，必需",
  "key_findings": ["主要发现1", "主要发现2", ...] // 字符串数组，必需
}

【字段说明】
1. research_question: 论文试图解决的核心问题或研究目标
2. method: 论文采用的研究方法、实验设计或分析框架
3. key_findings: 论文的主要发现和结论，以字符串数组形式列出

请严格按照 JSON 格式返回结果。"""

    @staticmethod
    def load_prompt(prompt_file: Optional[str] = None) -> str:
        """从文件加载提示词，如果未指定则使用默认提示词"""
        if prompt_file and Path(prompt_file).exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        # 尝试加载默认提示词文件
        default_prompt_path = Path("prompts/default.txt")
        if default_prompt_path.exists():
            return default_prompt_path.read_text(encoding='utf-8')
        return QwenClient.DEFAULT_SYSTEM_PROMPT

    def __init__(self):
        # 加载环境变量
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置，请检查 .env 文件")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = "qwen-long"

    def upload_pdf(self, pdf_path: str) -> str:
        """上传 PDF 到 DashScope，返回 file_id"""
        file_object = self.client.files.create(
            file=Path(pdf_path),
            purpose="file-extract"
        )
        return file_object.id

    def delete_file(self, file_id: str):
        """删除上传的文件"""
        try:
            self.client.files.delete(file_id)
        except Exception:
            pass  # 忽略删除失败

    def analyze_pdf(self, pdf_path: str,
                    system_prompt: Optional[str] = None,
                    temperature: float = 0.3,
                    max_tokens: int = 4096) -> Dict[str, Any]:
        """
        分析 PDF 文件

        Args:
            pdf_path: PDF 文件路径
            system_prompt: 自定义 prompt，使用默认 prompt 如果为 None
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            解析后的 JSON 字典
        """
        file_id = None
        try:
            # 上传 PDF
            file_id = self.upload_pdf(pdf_path)

            # 构造消息
            prompt = system_prompt or self.load_prompt()
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "system",
                    "content": f"fileid://{file_id}"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # 调用 API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                temperature=temperature
            )

            # 解析结果
            content = response.choices[0].message.content
            result = json.loads(content)
            result['_raw_response'] = content  # 保留原始响应
            return result

        finally:
            # 清理上传的文件
            if file_id:
                self.delete_file(file_id)

    def compute_cache_key(self, pdf_path: str, prompt: str, model: str) -> str:
        """计算缓存 key"""
        # 读取 PDF 内容计算 hash
        pdf_hash = compute_file_hash(pdf_path)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
        return f"{pdf_hash}_{prompt_hash}_{model}"


def compute_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """计算文件 hash"""
    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()
