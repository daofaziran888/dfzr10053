"""DAG快照领域服务：版本化图管理、拓扑层级查询与边校验。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class DagSnapshotService(BaseModuleService):
    MODULE = "dag_snapshot"
    ENTITY = "图快照"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["快照编号", "批次标识", "节点数量", "边数量", "快照时间", "版本标记"]
    REQUIRED_FIELDS = ["快照编号", "批次标识", "节点数量"]
    STATUS_ORDER = ["生成中", "待发布", "已发布", "已作废"]
    ACTION_RULES = {"提交发布": "待发布", "确认发布": "已发布", "作废快照": "已作废"}
    NEGATIVE_ACTIONS = ["作废快照"]

    def get_published_snapshot(self) -> dict[str, Any] | None:
        """获取最近一次已发布的快照。"""
        published = [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已发布"
        ]
        if not published:
            return None
        return max(published, key=lambda r: str(r.get("快照时间", "")))

    def get_layers(self, snap_id: str) -> list[list[str]]:
        """获取指定快照的拓扑层级。"""
        for r in store.rows(self.MODULE):
            if r.get("快照编号") == snap_id:
                return r.get("layers", [])
        return []

    def get_edges(self, snap_id: str) -> list[dict[str, Any]]:
        """获取指定快照的边列表。"""
        for r in store.rows(self.MODULE):
            if r.get("快照编号") == snap_id:
                return r.get("edges", [])
        return []

    def count_nodes(self, snap_id: str) -> int:
        """获取快照节点数量，-1 表示不存在。"""
        for r in store.rows(self.MODULE):
            if r.get("快照编号") == snap_id:
                return int(r.get("节点数量", "0"))
        return -1

    def is_obsolete(self, snap_id: str) -> bool:
        """检查快照是否已作废。"""
        for r in store.rows(self.MODULE):
            if r.get("快照编号") == snap_id:
                return r.get("status") == "已作废"
        return False