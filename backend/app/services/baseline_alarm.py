"""基线预警·计算管理，产出预警记录数据集。

领域方法：分级汇总、处置跟踪与解除状态校验。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class BaselineAlarmService(BaseModuleService):
    MODULE = "baseline_alarm"
    ENTITY = "预警记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["预警编号", "批次标识", "基线时间", "预计完成", "偏差分钟", "预警级别", "预警时间"]
    REQUIRED_FIELDS = ["预警编号", "批次标识", "基线时间"]
    STATUS_ORDER = ["已触发", "确认中", "已处置", "已解除"]
    ACTION_RULES = {"提交确认": "确认中", "处置预警": "已处置", "解除预警": "已解除"}
    NEGATIVE_ACTIONS = []

    def active_alarms(self) -> list[dict[str, Any]]:
        """获取未解除的活跃预警。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") != "已解除"
        ]

    def alarms_by_level(self, level: str) -> list[dict[str, Any]]:
        """按预警级别筛选。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("预警级别") == level
        ]

    def alarm_summary(self) -> dict[str, int]:
        """按级别汇总预警数量。"""
        rows = store.rows(self.MODULE)
        active = [r for r in rows if r.get("status") != "已解除"]
        summary: dict[str, int] = {}
        for r in active:
            level = str(r.get("预警级别", ""))
            summary[level] = summary.get(level, 0) + 1
        summary["total_active"] = len(active)
        return summary

    def worst_deviation(self) -> dict[str, Any] | None:
        """获取偏差分钟数最大的预警。"""
        active = self.active_alarms()
        if not active:
            return None
        return max(active, key=lambda r: int(r.get("偏差分钟", "0")))