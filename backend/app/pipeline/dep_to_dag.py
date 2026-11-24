"""依赖登记→DAG快照：将已生效依赖条目构建版本化有向无环图快照。

核心行为：
- 从 dep_registry 读取已生效依赖条目
- 提取节点全集并构建邻接表
- 检测强/弱依赖类型对编排顺序的影响
- 生成节点+边的版本化快照写入 dag_snapshot
- 快照版本标记由登记时间最新的依赖的时间戳生成
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DagNode:
    """DAG节点：代表一个批次。"""
    node_id: str
    batch: str
    indegree: int = 0
    outdegree: int = 0
    strong_deps: list[str] = field(default_factory=list)
    weak_deps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "batch": self.batch,
            "indegree": self.indegree,
            "outdegree": self.outdegree,
            "strong_deps": self.strong_deps,
            "weak_deps": self.weak_deps,
        }


class DepToDagEngine:
    """依赖登记到DAG转换引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store

    def build_dag_snapshot(
        self, snapshot_id: str, version_tag: str = "v1.0",
    ) -> dict[str, Any]:
        """从已生效依赖构建DAG快照。"""
        deps = self._store.rows("dep_registry")
        effective = [d for d in deps if d.get("status") == "已生效"]

        # 收集全部节点
        batch_set: set[str] = set()
        for dep in effective:
            batch_set.add(str(dep.get("下游批次", "")))
            batch_set.add(str(dep.get("上游批次", "")))

        nodes: dict[str, DagNode] = {}
        for batch_name in batch_set:
            nodes[batch_name] = DagNode(node_id=batch_name, batch=batch_name)

        # 构建邻接关系
        edges: list[dict[str, Any]] = []
        for dep in effective:
            downstream = str(dep.get("下游批次", ""))
            upstream = str(dep.get("上游批次", ""))
            dep_type = str(dep.get("依赖类型", "强依赖"))

            if downstream in nodes and upstream in nodes:
                downstream_node = nodes[downstream]
                downstream_node.indegree += 1
                if dep_type == "强依赖":
                    downstream_node.strong_deps.append(upstream)
                else:
                    downstream_node.weak_deps.append(upstream)
                nodes[upstream].outdegree += 1

                edges.append({
                    "from": upstream,
                    "to": downstream,
                    "dep_type": dep_type,
                    "生效日期": dep.get("生效日期", ""),
                    "依赖编号": dep.get("依赖编号", ""),
                })

        # 计算拓扑层数
        layers = self._compute_layers(edges, nodes)

        snapshot = {
            "快照编号": snapshot_id,
            "批次标识": version_tag,
            "节点数量": len(nodes),
            "边数量": len(edges),
            "快照时间": version_tag,
            "版本标记": version_tag,
            "nodes": [n.to_dict() for n in nodes.values()],
            "edges": edges,
            "layers": layers,
        }

        # 写入存储
        self._store.rows("dag_snapshot").append({
            "id": max(
                (int(r.get("id", 0)) for r in self._store.rows("dag_snapshot")),
                default=0,
            ) + 1,
            "快照编号": snapshot_id,
            "批次标识": version_tag,
            "节点数量": len(nodes),
            "边数量": len(edges),
            "快照时间": version_tag,
            "版本标记": version_tag,
            "status": "待发布",
            "pending": True,
            "abnormal": False,
            "layers": layers,
        })

        return snapshot

    def _compute_layers(
        self,
        edges: list[dict[str, Any]],
        nodes: dict[str, DagNode],
    ) -> list[list[str]]:
        """拓扑排序计算层级：每层节点无层间依赖。"""
        remaining = set(nodes.keys())
        in_degree: dict[str, int] = {
            n: nodes[n].indegree for n in remaining
        }

        layers: list[list[str]] = []
        while remaining:
            current_layer = sorted([
                n for n in remaining if in_degree.get(n, 0) == 0
            ])
            if not current_layer:
                # 存在环，取最小入度节点强行推进
                current_layer = sorted([
                    n for n in remaining
                ], key=lambda x: in_degree.get(x, 0))[:1]

            layers.append(current_layer)
            for node in current_layer:
                remaining.discard(node)
                for edge in edges:
                    if edge.get("from") == node and edge.get("to") in in_degree:
                        in_degree[edge["to"]] = max(0, in_degree[edge["to"]] - 1)

        return layers

    def query_strong_deps(self, batch: str) -> list[str]:
        """查询某批次的全部强依赖上游。"""
        deps = self._store.rows("dep_registry")
        return [
            d.get("上游批次", "")
            for d in deps
            if d.get("下游批次") == batch
            and d.get("依赖类型") == "强依赖"
            and d.get("status") == "已生效"
        ]

    def query_weak_deps(self, batch: str) -> list[str]:
        """查询某批次的全部弱依赖上游。"""
        deps = self._store.rows("dep_registry")
        return [
            d.get("上游批次", "")
            for d in deps
            if d.get("下游批次") == batch
            and d.get("依赖类型") == "弱依赖"
            and d.get("status") == "已生效"
        ]