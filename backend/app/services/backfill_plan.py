"""补数计划·校验管理，产出补数单数据集。

领域方法：范围判定、传播深度校验与审批状态汇总。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class BackfillPlanService(BaseModuleService):
    MODULE = "backfill_plan"
    ENTITY = "补数单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["补数编号", "批次标识", "业务日期起", "业务日期止", "传播深度", "创建时间"]
    REQUIRED_FIELDS = ["补数编号", "批次标识", "业务日期起"]
    STATUS_ORDER = ["草拟中", "待审批", "执行中", "已完成"]
    ACTION_RULES = {"提交审批": "待审批", "启动补数": "执行中", "确认完成": "已完成"}
    NEGATIVE_ACTIONS = []

    def active_plans(self) -> list[dict[str, Any]]:
        """获取执行中与待审批的补数单。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") in ("待审批", "执行中")
        ]

    def plans_for_batch(self, batch: str) -> list[dict[str, Any]]:
        """获取指定批次的所有补数单。"""
        return [
            r for r in store.rows(self.MODULE)
            if str(r.get("批次标识", "")) == batch
        ]

    def cascading_plans(self) -> list[dict[str, Any]]:
        """获取传播深度>0的补数单（会级联下游）。"""
        return [
            r for r in store.rows(self.MODULE)
            if int(r.get("传播深度", "0")) > 0
        ]

    def completion_breakdown(self) -> dict[str, int]:
        """按状态汇总补数单完成情况。"""
        rows = store.rows(self.MODULE)
        return {
            status: sum(1 for r in rows if r.get("status") == status)
            for status in self.STATUS_ORDER
        }

    def date_range_days(self, plan_id: str) -> int:
        """计算补数单覆盖的日期区间天数。"""
        for r in store.rows(self.MODULE):
            if r.get("补数编号") == plan_id:
                start = str(r.get("业务日期起", ""))
                end = str(r.get("业务日期止", ""))
                try:
                    s = (int(start.split("-")[0]) * 365
                         + int(start.split("-")[1]) * 30
                         + int(start.split("-")[2]))
                    e = (int(end.split("-")[0]) * 365
                         + int(end.split("-")[1]) * 30
                         + int(end.split("-")[2]))
                    return max(0, e - s + 1)
                except (ValueError, IndexError):
                    return 0
        return 0