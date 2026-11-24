"""SLA目标领域服务：时效校验、偏差统计与达标率计算。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class SlaTargetService(BaseModuleService):
    MODULE = "sla_target"
    ENTITY = "目标条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["目标编号", "批次标识", "目标完成时间", "时效要求", "统计周期", "更新时间"]
    REQUIRED_FIELDS = ["目标编号", "批次标识", "目标完成时间"]
    STATUS_ORDER = ["草拟中", "待生效", "已生效", "已废止"]
    ACTION_RULES = {"提交生效": "待生效", "生效目标": "已生效", "废止目标": "已废止"}
    NEGATIVE_ACTIONS = ["废止目标"]

    def effective_targets(self) -> list[dict[str, Any]]:
        """获取所有已生效的SLA目标。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已生效"
        ]

    def target_for_batch(self, batch: str) -> dict[str, Any] | None:
        """获取指定批次的已生效SLA目标。"""
        for r in self.effective_targets():
            if str(r.get("批次标识", "")) == batch:
                return r
        return None

    def target_time_for_batch(self, batch: str) -> str:
        """获取指定批次的目标完成时间。"""
        target = self.target_for_batch(batch)
        if not target:
            return ""
        return str(target.get("目标完成时间", ""))

    def obsoleted_targets(self) -> list[dict[str, Any]]:
        """获取所有已废止的SLA目标。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已废止"
        ]

    def deviation_from_target(self, batch: str, actual_time: str) -> int:
        """计算实际时间相对于目标时间的偏差分钟数。"""
        target_time = self.target_time_for_batch(batch)
        if not target_time:
            return 0
        try:
            t_h, t_m = (int(p) for p in target_time.split(":"))
            a_h, a_m = (int(p) for p in actual_time.split(":"))
            target_minutes = t_h * 60 + t_m
            actual_minutes = a_h * 60 + a_m
            return max(0, actual_minutes - target_minutes)
        except (ValueError, IndexError):
            return 0