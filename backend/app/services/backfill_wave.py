"""补数波次领域服务：波次推进判定、部分失败检测与完成度统计。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class BackfillWaveService(BaseModuleService):
    MODULE = "backfill_wave"
    ENTITY = "波次批次"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["波次编号", "补数编号", "波次序", "实例数量", "完成数量", "生成时间"]
    REQUIRED_FIELDS = ["波次编号", "补数编号", "波次序"]
    STATUS_ORDER = ["待执行", "执行中", "已完成", "部分失败"]
    ACTION_RULES = {"发起执行": "执行中", "确认完成": "已完成", "登记部分失败": "部分失败"}
    NEGATIVE_ACTIONS = ["登记部分失败"]

    def waves_for_plan(self, plan_id: str) -> list[dict[str, Any]]:
        """获取指定补数单的所有波次，按波次序排序。"""
        waves = [
            r for r in store.rows(self.MODULE)
            if r.get("补数编号") == plan_id
        ]
        waves.sort(key=lambda r: int(r.get("波次序", "0")))
        return waves

    def is_all_complete(self, plan_id: str) -> bool:
        """判定该补数单的所有波次是否已完成或部分失败。"""
        waves = self.waves_for_plan(plan_id)
        return all(
            w.get("status") in ("已完成", "部分失败")
            for w in waves
        )

    def partial_failed_waves(self) -> list[dict[str, Any]]:
        """获取所有部分失败的波次。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "部分失败"
        ]

    def completion_progress(self, plan_id: str) -> dict[str, Any]:
        """计算补数单的波次完成进度。"""
        waves = self.waves_for_plan(plan_id)
        completed = sum(
            1 for w in waves if w.get("status") == "已完成"
        )
        return {
            "plan_id": plan_id,
            "total_waves": len(waves),
            "completed": completed,
            "progress": completed / len(waves) if waves else 0.0,
        }