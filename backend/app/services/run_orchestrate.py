"""运行编排·校验管理，产出编排记录数据集。

领域方法：编排轮次分析、跳过原因汇总与异常检测。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class RunOrchestrateService(BaseModuleService):
    MODULE = "run_orchestrate"
    ENTITY = "编排记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["编排编号", "实例编号", "就绪数量", "跳过数量", "编排轮次", "编排时间"]
    REQUIRED_FIELDS = ["编排编号", "实例编号", "就绪数量"]
    STATUS_ORDER = ["编排中", "待复核", "已完成", "编排异常"]
    ACTION_RULES = {"提交复核": "待复核", "确认完成": "已完成", "登记异常": "编排异常"}
    NEGATIVE_ACTIONS = ["登记异常"]

    def get_skip_reasons(self, orch_id: str) -> dict[str, str]:
        """获取编排记录中全部跳过原因。"""
        for r in store.rows(self.MODULE):
            if r.get("编排编号") == orch_id:
                return r.get("skip_reasons", {})
        return {}

    def anomaly_orchestrations(self) -> list[dict[str, Any]]:
        """获取所有编排异常记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "编排异常"
        ]

    def compute_skip_rate(self, orch_id: str) -> float:
        """计算编排的跳过率：跳过数量 / (就绪+跳过)。"""
        for r in store.rows(self.MODULE):
            if r.get("编排编号") == orch_id:
                ready = int(r.get("就绪数量", "0"))
                skip = int(r.get("跳过数量", "0"))
                total = ready + skip
                return skip / total if total > 0 else 0.0
        return 0.0

    def orchestration_for_date(self, biz_date: str) -> dict[str, Any] | None:
        """获取指定日期的编排记录（最新）。"""
        best = None
        for r in store.rows(self.MODULE):
            if r.get("业务日期") == biz_date:
                if best is None or r.get("编排时间", "") > best.get("编排时间", ""):
                    best = r
        return best