"""阿里云百炼客户端"""

from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Config
from .json_utils import parse_json_with_retry, save_json
from .logging_utils import setup_logger

logger = setup_logger(__name__)


class BailianClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _call_model(self, messages: list[dict]) -> str:
        resp = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=0.1,
            max_tokens=32768,
        )
        return resp.choices[0].message.content or ""

    def build_video_message(self, prompt: str, video_url: str | None = None, video_path: str | None = None) -> list[dict]:
        """构建视频分析消息。

        支持两种方式：
        1. video_url: 公网 URL（首选）
        2. video_path: 本地文件路径，用 base64 编码（限制 20MB）
        """
        content: list[dict] = [{"type": "text", "text": prompt}]

        if video_url:
            content.append({"type": "video_url", "video_url": {"url": video_url}})
        elif video_path:
            path = Path(video_path)
            if not path.exists():
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            size_mb = path.stat().st_size / 1024 / 1024
            if size_mb > 20:
                raise ValueError(
                    f"视频文件过大 ({size_mb:.1f}MB)，base64 方式限制 20MB，请使用公网 URL"
                )

            logger.info(f"使用 base64 编码本地视频: {video_path} ({size_mb:.1f}MB)")
            with open(path, "rb") as f:
                video_data = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "video_url",
                "video_url": {"url": f"data:video/mp4;base64,{video_data}"},
            })
        else:
            raise ValueError("必须提供 video_url 或 video_path")

        return [{"role": "user", "content": content}]

    def analyze_video(
        self,
        prompt: str,
        video_url: str | None,
        video_path: str | None,
        save_dir: Path,
    ) -> dict:
        """调用模型分析视频，返回解析后的 JSON dict。"""
        logger.info(f"调用模型 {self.config.model} 分析视频...")
        messages = self.build_video_message(prompt, video_url=video_url, video_path=video_path)
        raw = self._call_model(messages)

        # 保存原始输出
        save_json({"raw_response": raw}, save_dir / "analysis_raw.json")

        return parse_json_with_retry(
            raw,
            max_retries=2,
            error_log_path=save_dir / "debug_parse_failed.txt",
        )
