"""传播追踪领域服务：路径分析、深度检查与变更范围汇总。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class PropagationTraceService(BaseModuleService):
    MODULE = "propagation_trace"
    ENTITY = "追踪明细"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["追踪编号", "补数编号", "传播路径", "受影响实例", "追踪深度", "生成时间"]
    REQUIRED_FIELDS = ["追踪编号", "补数编号", "传播路径"]
    STATUS_ORDER = ["追踪中", "待确认", "已确认", "路径存疑"]
    ACTION_RULES = {"提交确认": "待确认", "确认路径": "已确认", "登记存疑": "路径存疑"}
    NEGATIVE_ACTIONS = ["登记存疑"]

    def trace_for_plan(self, plan_id: str) -> dict[str, Any] | None:
        """获取指定补数单的传播追踪记录。"""
        for r in store.rows(self.MODULE):
            if r.get("补数编号") == plan_id:
                return r
        return None

    def confirmed_traces(self) -> list[dict[str, Any]]:
        """获取所有已确认的追踪记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已确认"
        ]

    def suspicious_traces(self) -> list[dict[str, Any]]:
        """获取路径存疑的追踪记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "路径存疑"
        ]

    def max_depth_trace(self) -> dict[str, Any] | None:
        """获取传播深度最大的追踪记录。"""
        traces = store.rows(self.MODULE)
        if not traces:
            return None
        return max(traces, key=lambda r: int(r.get("追踪深度", "0")))

    def affected_count(self, plan_id: str) -> int:
        """获取补数单的受影响实例数量。"""
        trace = self.trace_for_plan(plan_id)
        if not trace:
            return 0
        return int(trace.get("受影响实例", "0"))