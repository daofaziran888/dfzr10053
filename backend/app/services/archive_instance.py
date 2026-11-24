"""归档实例领域服务：保留期检查、可回取判定与销毁管理。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class ArchiveInstanceService(BaseModuleService):
    MODULE = "archive_instance"
    ENTITY = "归档记录"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["归档编号", "实例编号", "归档层级", "归档时间", "保留天数", "可回取标记"]
    REQUIRED_FIELDS = ["归档编号", "实例编号", "归档层级"]
    STATUS_ORDER = ["待归档", "归档中", "已归档", "已销毁"]
    ACTION_RULES = {"发起归档": "归档中", "确认归档": "已归档", "销毁归档": "已销毁"}
    NEGATIVE_ACTIONS = ["销毁归档"]

    def restorable(self) -> list[dict[str, Any]]:
        """获取可回取的归档记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("可回取标记") == "是"
            and r.get("status") == "已归档"
        ]

    def non_restorable(self) -> list[dict[str, Any]]:
        """获取不可回取的归档记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("可回取标记") == "否"
            or r.get("status") == "已销毁"
        ]

    def archives_for_instance(self, instance_id: str) -> list[dict[str, Any]]:
        """获取指定实例的归档记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if str(r.get("实例编号", "")) == instance_id
        ]

    def archived_count(self) -> int:
        """统计已归档且可回取的数量。"""
        return sum(
            1 for r in store.rows(self.MODULE)
            if r.get("status") == "已归档"
            and r.get("可回取标记") == "是"
        )

    def by_layer(self) -> dict[str, int]:
        """按归档层级统计数量。"""
        counts: dict[str, int] = {}
        for r in store.rows(self.MODULE):
            layer = str(r.get("归档层级", ""))
            counts[layer] = counts.get(layer, 0) + 1
        return counts