"""依赖登记·校验管理，产出依赖条目数据集。

领域方法：上下游关系管理、拓扑判定与环路检测。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class DepRegistryService(BaseModuleService):
    MODULE = "dep_registry"
    ENTITY = "依赖条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["依赖编号", "下游批次", "上游批次", "依赖类型", "生效日期", "登记时间"]
    REQUIRED_FIELDS = ["依赖编号", "下游批次", "上游批次"]
    STATUS_ORDER = ["草稿", "待确认", "已生效", "已失效"]
    ACTION_RULES = {"提交确认": "待确认", "生效依赖": "已生效", "失效依赖": "已失效"}
    NEGATIVE_ACTIONS = []

    def get_effective_deps(self) -> list[dict[str, Any]]:
        """获取全部已生效依赖条目。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已生效"
        ]

    def upstream_of(self, batch: str) -> list[dict[str, Any]]:
        """查找指定批次的所有上游依赖，按依赖类型排序：强依赖在前。"""
        deps = self.get_effective_deps()
        result = [
            d for d in deps if d.get("下游批次") == batch
        ]
        result.sort(key=lambda d: 0 if d.get("依赖类型") == "强依赖" else 1)
        return result

    def downstream_of(self, batch: str) -> list[dict[str, Any]]:
        """查找指定批次的所有下游消费者。"""
        deps = self.get_effective_deps()
        return [d for d in deps if d.get("上游批次") == batch]

    def detect_circular(self) -> list[list[str]]:
        """检测依赖图中的环路：返回形成环的批次链。"""
        deps = self.get_effective_deps()
        adj: dict[str, list[str]] = {}
        for d in deps:
            adj.setdefault(str(d.get("上游批次", "")), []).append(
                str(d.get("下游批次", "")),
            )
        # DFS 环路检测
        visited: set[str] = set()
        path: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, chain: list[str]) -> None:
            if node in path:
                cycle_start = chain.index(node)
                cycles.append(chain[cycle_start:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            path.add(node)
            for child in adj.get(node, []):
                dfs(child, chain + [node])
            path.discard(node)

        for node in adj:
            if node not in visited:
                dfs(node, [])
        return cycles