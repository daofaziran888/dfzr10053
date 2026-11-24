"""补数计划→补数波次：将补数单按依赖层级拆分为波次批次。

核心行为：
- 从 backfill_plan 读取执行中的补数单
- 根据传播深度从 DAG 快照计算受影响节点集
- 按 DAG 层级拆分为多个波次（同波次可并行、跨波次串行）
- 波次拆分结果写入 backfill_wave
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BackfillWaveSplit:
    """波次拆分结果。"""
    plan_id: str
    batch: str
    total_waves: int
    wave_instances: dict[int, list[str]] = field(default_factory=dict)


class PlanToWaveEngine:
    """补数计划到波次转发引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store

    def split_to_waves(
        self, plan_id: str, dag_snap_id: str | None = None,
    ) -> dict[str, Any]:
        """将补数单拆分为多个波次。"""
        plan = self._find_plan(plan_id)
        if not plan:
            return {"error": f"补数单 {plan_id} 不存在", "waves": []}

        batch = str(plan.get("批次标识", ""))
        start_date = str(plan.get("业务日期起", ""))
        end_date = str(plan.get("业务日期止", ""))
        depth = int(plan.get("传播深度", "0"))

        # 从 DAG 快照获取受影响节点
        snap = self._pick_snapshot(dag_snap_id, batch)
        if not snap:
            return {"error": "无可用DAG快照", "waves": []}

        affected_nodes = self._compute_affected_nodes(
            snap, batch, depth,
        )
        layers = snap.get("layers", [])

        # 按层级将受影响节点拆分为波次
        wave_order = 0
        waves_out: list[dict[str, Any]] = []
        layer_nodes: dict[int, list[str]] = {}

        for layer_idx, layer in enumerate(layers):
            layer_affected = [
                n for n in layer if n in affected_nodes
            ]
            if layer_affected:
                wave_order += 1
                layer_nodes[wave_order] = layer_affected

                wave_entry = {
                    "id": max(
                        (int(r.get("id", 0))
                         for r in self._store.rows("backfill_wave")),
                        default=0,
                    ) + wave_order,
                    "波次编号": f"WAVE_{plan_id}_{wave_order}",
                    "补数编号": plan_id,
                    "波次序": str(wave_order),
                    "实例数量": len(layer_affected),
                    "完成数量": 0,
                    "生成时间": start_date,
                    "status": "待执行",
                    "pending": True,
                    "abnormal": False,
                    "affected_nodes": layer_affected,
                }
                self._store.rows("backfill_wave").append(wave_entry)
                waves_out.append({
                    "wave_order": wave_order,
                    "wave_id": wave_entry["波次编号"],
                    "instance_count": len(layer_affected),
                    "nodes": layer_affected,
                })

        # 更新补数单状态
        plan["status"] = "执行中"
        plan["pending"] = True

        return {
            "plan_id": plan_id,
            "batch": batch,
            "depth": depth,
            "total_waves": wave_order,
            "waves": waves_out,
        }

    def _find_plan(self, plan_id: str) -> dict[str, Any] | None:
        for r in self._store.rows("backfill_plan"):
            if r.get("补数编号") == plan_id:
                return r
        return None

    def _pick_snapshot(
        self, snap_id: str | None, batch: str,
    ) -> dict[str, Any] | None:
        if snap_id:
            for r in self._store.rows("dag_snapshot"):
                if r.get("快照编号") == snap_id:
                    return r
        # 自动选择最新已发布且包含该批次的快照
        for r in self._store.rows("dag_snapshot"):
            if r.get("status") != "已发布":
                continue
            edges = r.get("edges", [])
            nodes = r.get("node_names", [])
            if batch in nodes:
                return r
            for e in edges:
                if e.get("from") == batch or e.get("to") == batch:
                    return r
        return None

    def _compute_affected_nodes(
        self, snap: dict[str, Any], root_batch: str, depth: int,
    ) -> set[str]:
        """BFS计算传播范围内的受影响节点。"""
        edges = snap.get("edges", [])
        adj: dict[str, list[str]] = {}
        for e in edges:
            adj.setdefault(e.get("from", ""), []).append(e.get("to", ""))

        affected: set[str] = {root_batch}
        queue = [(root_batch, 0)]
        while queue:
            node, d = queue.pop(0)
            if d >= depth and depth > 0:
                continue
            for child in adj.get(node, []):
                if child not in affected:
                    affected.add(child)
                    queue.append((child, d + 1))

        return affected