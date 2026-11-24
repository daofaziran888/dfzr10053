"""冲突解决·校验管理，产出解决记录数据集。

领域方法：冲突类型分类、解决方案推荐与未解决跟踪。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class ConflictResolveService(BaseModuleService):
    MODULE = "conflict_resolve"
    ENTITY = "解决记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["解决编号", "冲突实例", "冲突类型", "解决方案", "操作者", "解决时间"]
    REQUIRED_FIELDS = ["解决编号", "冲突实例", "冲突类型"]
    STATUS_ORDER = ["已发现", "处置中", "已解决", "升级处理"]
    ACTION_RULES = {"发起处置": "处置中", "确认解决": "已解决", "升级冲突": "升级处理"}
    NEGATIVE_ACTIONS = ["升级冲突"]

    def unresolved_conflicts(self) -> list[dict[str, Any]]:
        """获取未解决的冲突（已发现+处置中）。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") in ("已发现", "处置中")
        ]

    def escalated_conflicts(self) -> list[dict[str, Any]]:
        """获取升级处理的冲突。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "升级处理"
        ]

    def conflicts_by_type(self) -> dict[str, int]:
        """按冲突类型统计数量。"""
        rows = store.rows(self.MODULE)
        counts: dict[str, int] = {}
        for r in rows:
            ctype = str(r.get("冲突类型", ""))
            counts[ctype] = counts.get(ctype, 0) + 1
        return counts

    def conflicts_for_instance(self, instance_id: str) -> list[dict[str, Any]]:
        """获取涉及指定实例的冲突。"""
        return [
            r for r in store.rows(self.MODULE)
            if instance_id in str(r.get("冲突实例", ""))
        ]

    def freeze_block_count(self) -> int:
        """统计冻结拦截类冲突的数量。"""
        return sum(
            1 for r in store.rows(self.MODULE)
            if r.get("冲突类型") == "冻结拦截"
        )