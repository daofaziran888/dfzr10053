"""运行配置：端口、跨域、运行环境。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    app_name: str = "承排工坊 · 批次依赖编排与补数传播平台"
    env: str = "local"
    port: int = 8010
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            "http://127.0.0.1:5183",
            "http://localhost:5183",
        ]
    )
    page_size_default: int = 20
    page_size_max: int = 200


settings = Settings()
