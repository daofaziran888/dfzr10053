"""预演跑领域服务：预估校验、预演覆盖率计算与结果评审。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class DryRunService(BaseModuleService):
    MODULE = "dry_run"
    ENTITY = "预演单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["预演编号", "补数编号", "预演范围", "预计实例数", "预计耗时", "预演时间"]
    REQUIRED_FIELDS = ["预演编号", "补数编号", "预演范围"]
    STATUS_ORDER = ["预演中", "待评审", "已评审", "已作废"]
    ACTION_RULES = {"提交评审": "待评审", "确认评审": "已评审", "作废预演": "已作废"}
    NEGATIVE_ACTIONS = ["作废预演"]

    def dry_runs_for_plan(self, plan_id: str) -> list[dict[str, Any]]:
        """获取指定补数单的预演记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("补数编号") == plan_id
        ]

    def pending_review(self) -> list[dict[str, Any]]:
        """获取待评审的预演单。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "待评审"
        ]

    def total_estimated_instances(self, plan_id: str) -> int:
        """计算某补数单所有预演预估的总实例数。"""
        runs = self.dry_runs_for_plan(plan_id)
        return sum(int(r.get("预计实例数", "0")) for r in runs)

    def latest_for_plan(self, plan_id: str) -> dict[str, Any] | None:
        """获取指定补数单的最新预演记录。"""
        runs = self.dry_runs_for_plan(plan_id)
        if not runs:
            return None
        return max(runs, key=lambda r: str(r.get("预演时间", "")))

    def estimated_duration_minutes(self, plan_id: str) -> int:
        """计算某补数单预演的总预计耗时（分钟）。"""
        runs = self.dry_runs_for_plan(plan_id)
        total = 0
        for r in runs:
            dur = str(r.get("预计耗时", "0分钟"))
            try:
                total += int(dur.replace("分钟", ""))
            except ValueError:
                pass
        return total