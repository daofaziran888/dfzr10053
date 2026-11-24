"""资源配额·计算管理，产出配额条目数据集。

领域方法：并发度校验、超限判定与排队计算。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class ResourceQuotaService(BaseModuleService):
    MODULE = "resource_quota"
    ENTITY = "配额条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["配额编号", "队列标识", "并发上限", "占用并发", "排队数量", "配额周期", "更新时间"]
    REQUIRED_FIELDS = ["配额编号", "队列标识", "并发上限"]
    STATUS_ORDER = ["计量中", "待复核", "已确认", "已调整"]
    ACTION_RULES = {"提交复核": "待复核", "确认配额": "已确认", "调整配额": "已调整"}
    NEGATIVE_ACTIONS = []

    def get_quota(self, queue: str) -> dict[str, Any] | None:
        """获取指定队列的配额信息。"""
        for r in store.rows(self.MODULE):
            if r.get("队列标识") == queue:
                return r
        return None

    def available_slots(self, queue: str) -> int:
        """计算队列剩余可用并发槽位数。"""
        quota = self.get_quota(queue)
        if not quota:
            return 0
        cap = int(quota.get("并发上限", "0"))
        used = int(quota.get("占用并发", "0"))
        return max(0, cap - used)

    def is_overloaded(self, queue: str) -> bool:
        """判断队列是否超载（排队数量超过并发上限两倍）。"""
        quota = self.get_quota(queue)
        if not quota:
            return True
        cap = int(quota.get("并发上限", "0"))
        queued = int(quota.get("排队数量", "0"))
        return queued > cap * 2

    def overloaded_queues(self) -> list[str]:
        """列出所有超载队列的标识。"""
        queues: set[str] = {str(r.get("队列标识", "")) for r in store.rows(self.MODULE)}
        return [q for q in queues if self.is_overloaded(q)]

    def used_percentage(self, queue: str) -> float:
        """计算队列并发占用率。"""
        quota = self.get_quota(queue)
        if not quota:
            return 0.0
        cap = int(quota.get("并发上限", "0"))
        used = int(quota.get("占用并发", "0"))
        return used / cap if cap > 0 else 0.0