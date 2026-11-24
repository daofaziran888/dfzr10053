"""传播追踪：补数在依赖图上的传播路径计算与受影响实例清单生成。

核心行为：
- 从 backfill_plan 读取执行中的补数单
- 基于已发布 DAG 快照计算补数在依赖图中的传播路径
- 生成受影响实例清单写入 propagation_trace
- 传播路径上的每条边都记录为追踪明细
- 追踪结果作为波次拆分的输入
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropagationPath:
    """传播路径描述。"""
    plan_id: str
    root_batch: str
    depth: int
    path_nodes: list[str] = field(default_factory=list)
    affected_instances: list[str] = field(default_factory=list)


class PropagationTracingEngine:
    """传播追踪引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store

    def trace_propagation(self, plan_id: str) -> dict[str, Any]:
        """计算补数传播路径。"""
        plan = self._find_plan(plan_id)
        if not plan:
            return {"error": f"补数单 {plan_id} 不存在"}

        batch = str(plan.get("批次标识", ""))
        depth = int(plan.get("传播深度", "0"))

        # 加载已发布 DAG
        snap = self._pick_published_snap(batch)
        if not snap:
            return {"error": "无已发布DAG快照"}

        edges = snap.get("edges", [])
        # 构建邻接表
        adj: dict[str, list[dict[str, Any]]] = {}
        for e in edges:
            adj.setdefault(e.get("from", ""), []).append(e)

        # BFS 计算传播路径
        path_nodes: list[list[str]] = []
        affected_instances: list[str] = []
        visited: set[str] = set()

        current_layer = [batch]
        current_depth = 0

        while current_layer and current_depth <= depth + 1:
            path_nodes.append(list(current_layer))
            next_layer: list[str] = []

            for node in current_layer:
                if node in visited:
                    continue
                visited.add(node)
                for edge in adj.get(node, []):
                    to_node = edge.get("to", "")
                    if to_node not in visited:
                        next_layer.append(to_node)
                        # 找该批次对应实例
                        for inst in self._store.rows("batch_instance"):
                            if (str(inst.get("批次标识", "")) == to_node
                                    and str(inst.get("实例编号", ""))
                                    not in affected_instances):
                                affected_instances.append(
                                    str(inst.get("实例编号", "")),
                                )

            current_layer = next_layer
            current_depth += 1

        # 写入传播追踪记录
        trace_rows = self._store.rows("propagation_trace")
        path_str = "->".join(
            ",".join(layer) for layer in path_nodes
        )

        new_id = max(
            (int(r.get("id", 0)) for r in trace_rows), default=0,
        ) + 1
        trace_rows.append({
            "id": new_id,
            "追踪编号": f"TRACE_{plan_id}_{new_id}",
            "补数编号": plan_id,
            "传播路径": path_str,
            "受影响实例": ",".join(affected_instances),
            "追踪深度": str(len(path_nodes) - 1),
            "生成时间": plan.get("创建时间", ""),
            "status": "待确认",
            "pending": True,
            "abnormal": len(affected_instances) == 0,
            "path_layers": path_nodes,
        })

        return {
            "plan_id": plan_id,
            "root_batch": batch,
            "depth": depth,
            "path_layers": path_nodes,
            "affected_count": len(affected_instances),
            "affected_instances": affected_instances,
            "trace_id": f"TRACE_{plan_id}_{new_id}",
        }

    def _find_plan(self, plan_id: str) -> dict[str, Any] | None:
        for r in self._store.rows("backfill_plan"):
            if r.get("补数编号") == plan_id:
                return r
        return None

    def _pick_published_snap(
        self, batch: str,
    ) -> dict[str, Any] | None:
        for r in self._store.rows("dag_snapshot"):
            if r.get("status") != "已发布":
                continue
            # 检查快照的边数据中是否包含该批次
            edges = r.get("edges", [])
            if not edges:
                continue
            for e in edges:
                if e.get("from") == batch or e.get("to") == batch:
                    return r
            # 或者检查节点列表中是否包含该批次
            nodes = r.get("node_names", [])
            if batch in nodes:
                return r
        return None