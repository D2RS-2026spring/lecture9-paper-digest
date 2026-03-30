"""Batch API 模块 - 使用 Qwen Batch 接口批量处理文献

Batch API 费用为实时调用的 50%，适合批量处理文献。
"""

import os
import json
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from openai import OpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class BatchJob:
    """Batch 任务信息"""
    batch_id: str
    input_file_id: str
    status: str
    output_file_id: Optional[str] = None
    error_file_id: Optional[str] = None


@dataclass
class BatchResult:
    """Batch 分析结果"""
    custom_id: str
    success: bool
    content: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[str] = None


class QwenBatchClient:
    """Qwen Batch API 客户端"""

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

    def create_batch_request(self, paper_id: str, pdf_path: str,
                            custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        创建单个文献的 Batch 请求

        Args:
            paper_id: 文献 ID（用作 custom_id）
            pdf_path: PDF 文件路径
            custom_prompt: 自定义 prompt

        Returns:
            Batch 请求字典
        """
        # 上传 PDF
        file_id = self.upload_pdf(pdf_path)

        prompt = custom_prompt or self.DEFAULT_SYSTEM_PROMPT

        # 构造 Batch 请求
        request = {
            "custom_id": str(paper_id),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model,
                "messages": [
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
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 4096,
                "temperature": 0.3
            }
        }

        return request

    def create_batch_job(self, requests: List[Dict[str, Any]]) -> BatchJob:
        """
        创建 Batch 任务

        Args:
            requests: Batch 请求列表

        Returns:
            BatchJob 对象
        """
        # 创建临时 JSONL 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl',
                                         delete=False, encoding='utf-8') as f:
            for req in requests:
                f.write(json.dumps(req, ensure_ascii=False) + '\n')
            temp_path = f.name
        try:
            # 上传 JSONL 文件
            console.print(f"[dim]上传 Batch 输入文件 ({len(requests)} 个请求)...[/dim]")
            file_object = self.client.files.create(
                file=Path(temp_path),
                purpose="batch"
            )
            input_file_id = file_object.id

            # 创建 Batch 任务
            console.print("[dim]创建 Batch 任务...[/dim]")
            batch = self.client.batches.create(
                input_file_id=input_file_id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={
                    "ds_name": f"Paper Digest Batch ({len(requests)} papers)"
                }
            )

            return BatchJob(
                batch_id=batch.id,
                input_file_id=input_file_id,
                status=batch.status
            )

        finally:
            # 清理临时文件
            os.unlink(temp_path)

    def check_batch_status(self, batch_id: str) -> BatchJob:
        """
        检查 Batch 任务状态

        Args:
            batch_id: Batch 任务 ID

        Returns:
            BatchJob 对象
        """
        batch = self.client.batches.retrieve(batch_id=batch_id)

        return BatchJob(
            batch_id=batch.id,
            input_file_id=batch.input_file_id,
            status=batch.status,
            output_file_id=batch.output_file_id,
            error_file_id=batch.error_file_id
        )

    def download_results(self, output_file_id: str) -> List[BatchResult]:
        """
        下载 Batch 任务结果

        Args:
            output_file_id: 输出文件 ID

        Returns:
            BatchResult 列表
        """
        content = self.client.files.content(output_file_id)
        text = content.text

        results = []
        for line in text.strip().split('\n'):
            if not line:
                continue

            data = json.loads(line)
            custom_id = data.get('custom_id', '')
            error = data.get('error')
            response = data.get('response', {})

            if error:
                results.append(BatchResult(
                    custom_id=custom_id,
                    success=False,
                    error_message=f"{error.get('code')}: {error.get('message')}"
                ))
            elif response.get('status_code') == 200:
                body = response.get('body', {})
                choices = body.get('choices', [])
                if choices:
                    content_text = choices[0].get('message', {}).get('content', '')
                    results.append(BatchResult(
                        custom_id=custom_id,
                        success=True,
                        content=content_text,
                        raw_response=json.dumps(body, ensure_ascii=False)
                    ))
                else:
                    results.append(BatchResult(
                        custom_id=custom_id,
                        success=False,
                        error_message="No choices in response"
                    ))
            else:
                results.append(BatchResult(
                    custom_id=custom_id,
                    success=False,
                    error_message=f"Status code: {response.get('status_code')}"
                ))

        return results

    def cancel_batch(self, batch_id: str) -> bool:
        """
        取消 Batch 任务

        Args:
            batch_id: Batch 任务 ID

        Returns:
            是否成功取消
        """
        try:
            self.client.batches.cancel(batch_id)
            return True
        except Exception as e:
            console.print(f"[red]取消失败: {e}[/red]")
            return False

    def wait_for_completion(self, batch_id: str,
                           poll_interval: int = 60,
                           timeout: Optional[int] = None) -> BatchJob:
        """
        等待 Batch 任务完成

        Args:
            batch_id: Batch 任务 ID
            poll_interval: 轮询间隔（秒）
            timeout: 超时时间（秒），None 表示不超时

        Returns:
            BatchJob 对象
        """
        start_time = time.time()
        poll_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("等待 Batch 任务完成...", total=None)

            while True:
                job = self.check_batch_status(batch_id)
                poll_count += 1

                progress.update(task, description=f"Batch 状态: {job.status} (第 {poll_count} 次检查)")

                if job.status in ['completed', 'failed', 'expired', 'cancelled']:
                    return job

                # 检查超时
                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Batch 任务超时 (>{timeout}秒)")

                time.sleep(poll_interval)


def parse_batch_result(result: BatchResult) -> Optional[Dict[str, Any]]:
    """
    解析 Batch 结果内容为结构化数据

    Args:
        result: BatchResult 对象

    Returns:
        解析后的字典，失败返回 None
    """
    if not result.success or not result.content:
        return None

    try:
        data = json.loads(result.content)
        return {
            'research_question': data.get('research_question', ''),
            'method': data.get('method', ''),
            'key_findings': data.get('key_findings', []),
            'raw_response': result.raw_response or result.content
        }
    except json.JSONDecodeError:
        return None
