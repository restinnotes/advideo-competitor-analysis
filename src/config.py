"""配置管理"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str

    @classmethod
    def from_env(cls, model_override: str | None = None) -> "Config":
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if not api_key:
            raise ValueError("未设置 DASHSCOPE_API_KEY 环境变量")

        base_url = os.getenv(
            "BAILIAN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        model = model_override or os.getenv("BAILIAN_MODEL", "qwen3.5-omni-plus")
        return cls(api_key=api_key, base_url=base_url, model=model)