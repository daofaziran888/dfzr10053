"""队列调度领域服务：准入拒绝分析、排队统计与调度效率评估。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class QueueScheduleService(BaseModuleService):
    MODULE = "queue_schedule"
    ENTITY = "调度记录"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["调度编号", "队列标识", "调度轮次", "准入数量", "拒绝数量", "调度时间"]
    REQUIRED_FIELDS = ["调度编号", "队列标识", "调度轮次"]
    STATUS_ORDER = ["调度中", "待复核", "已完成", "调度异常"]
    ACTION_RULES = {"提交复核": "待复核", "确认完成": "已完成", "登记异常": "调度异常"}
    NEGATIVE_ACTIONS = ["登记异常"]

    def schedules_for_queue(self, queue: str) -> list[dict[str, Any]]:
        """获取指定队列的调度记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("队列标识") == queue
        ]

    def rejection_rate(self, queue: str) -> float:
        """计算队列的平均拒绝率。"""
        rows = self.schedules_for_queue(queue)
        if not rows:
            return 0.0
        total_admit = sum(int(r.get("准入数量", "0")) for r in rows)
        total_reject = sum(int(r.get("拒绝数量", "0")) for r in rows)
        total = total_admit + total_reject
        return total_reject / total if total > 0 else 0.0

    def latest_schedule(self, queue: str) -> dict[str, Any] | None:
        """获取指定队列的最新调度记录。"""
        rows = self.schedules_for_queue(queue)
        if not rows:
            return None
        return max(rows, key=lambda r: str(r.get("调度时间", "")))

    def anomaly_schedules(self) -> list[dict[str, Any]]:
        """获取调度异常的记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "调度异常"
        ]