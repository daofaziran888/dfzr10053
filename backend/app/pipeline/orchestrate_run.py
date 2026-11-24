"""批次实例→运行编排：按DAG层级逐轮判定实例就绪状态并生成编排记录。

核心行为：
- 读取已发布DAG快照的节点和层级结构
- 按层级顺序判定每个实例的就绪状态
- 上游全部成功且信号已消费的实例标记就绪
- 上游失败或存疑的实例标记跳过并生成跳过审计
- 编排完成时汇总跳过原因与就绪/跳过数量
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrchestrateRound:
    """编排轮次：一轮编排的判定结果。"""
    round_num: int
    ready_ids: list[str] = field(default_factory=list)
    skip_ids: list[str] = field(default_factory=list)
    skip_reasons: dict[str, str] = field(default_factory=dict)


class OrchestrateRunEngine:
    """编排运行引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store

    def orchestrate(
        self, snap_id: str, biz_date: str,
    ) -> dict[str, Any]:
        """对某快照按业务日期编排实例。"""
        snap_data = self._find_snapshot(snap_id)
        if not snap_data:
            return {"error": f"快照 {snap_id} 不存在", "rounds": []}

        layers = snap_data.get("layers", [])
        instances = self._store.rows("batch_instance")
        signals = self._store.rows("upstream_signal")

        # 筛选业务日期匹配的实例
        date_instances = [
            i for i in instances if str(i.get("业务日期", "")) == biz_date
        ]

        rounds: list[OrchestrateRound] = []
        round_num = 0
        advance_count = 0

        for layer in layers:
            round_num += 1
            round_record = OrchestrateRound(round_num=round_num)

            for node_name in layer:
                node_instances = [
                    i for i in date_instances
                    if str(i.get("批次标识", "")) == node_name
                ]
                for inst in node_instances:
                    instance_id = str(inst.get("实例编号", ""))
                    if inst.get("status") in ("已成功", "已失败"):
                        continue

                    # 检查上游信号
                    signal_ready = self._check_signal(
                        signals, node_name, biz_date,
                    )
                    if not signal_ready:
                        round_record.skip_ids.append(instance_id)
                        round_record.skip_reasons[instance_id] = (
                            f"上游批次 {node_name} 信号未就绪"
                        )
                        continue

                    # 检查所有上游实例状态
                    upstream_all_ok, block_reason = self._check_upstream(
                        snap_data, instances, biz_date, node_name,
                    )
                    if not upstream_all_ok:
                        round_record.skip_ids.append(instance_id)
                        round_record.skip_reasons[instance_id] = block_reason
                        continue

                    round_record.ready_ids.append(instance_id)
                    # 准入：将状态切为运行中
                    inst["status"] = "运行中"
                    inst["pending"] = True

            # 写入编排记录
            if round_record.ready_ids or round_record.skip_ids:
                self._write_orchestrate_record(
                    snap_id, round_num, round_record,
                )
                advance_count += len(round_record.ready_ids)
                rounds.append(round_record)

            # 如当前层有跳过实例，后续与下一层等待
            if round_record.skip_ids:
                for inst in [i for i in date_instances
                             if str(i.get("批次标识", "")) in layer
                             and i.get("status") == "待就绪"]:
                    inst["pending"] = True

        return {
            "snap_id": snap_id,
            "biz_date": biz_date,
            "total_rounds": len(rounds),
            "advance_count": advance_count,
            "rounds": [
                {
                    "round": r.round_num,
                    "ready": r.ready_ids,
                    "skip": r.skip_ids,
                    "skip_reasons": r.skip_reasons,
                }
                for r in rounds
            ],
        }

    def _find_snapshot(self, snap_id: str) -> dict[str, Any] | None:
        for r in self._store.rows("dag_snapshot"):
            if r.get("快照编号") == snap_id:
                return r
        return None

    def _check_signal(
        self, signals: list[dict[str, Any]], batch: str, biz_date: str,
    ) -> bool:
        for s in signals:
            if (str(s.get("上游批次", "")) == batch
                    and str(s.get("业务日期", "")) == biz_date
                    and s.get("status") == "已消费"):
                return True
        return False

    def _check_upstream(
        self, snap_data: dict[str, Any], instances: list[dict[str, Any]],
        biz_date: str, batch: str,
    ) -> tuple[bool, str]:
        """检查当前批次的全部上游实例是否已成功。"""
        edges = snap_data.get("edges", [])
        upstreams: set[str] = set()
        for e in edges:
            if e.get("to") == batch:
                upstreams.add(e.get("from", ""))

        if not upstreams:
            return True, ""

        for up_batch in upstreams:
            up_instances = [
                i for i in instances
                if str(i.get("批次标识", "")) == up_batch
                and str(i.get("业务日期", "")) == biz_date
            ]
            for up_inst in up_instances:
                if up_inst.get("status") == "已失败":
                    return False, f"上游实例 {up_inst.get('实例编号')} 已失败"
                if up_inst.get("status") != "已成功":
                    return False, f"上游实例 {up_inst.get('实例编号')} 状态未完成"
        return True, ""

    def _write_orchestrate_record(
        self, snap_id: str, round_num: int, record: OrchestrateRound,
    ) -> None:
        rows = self._store.rows("run_orchestrate")
        new_id = max(
            (int(r.get("id", 0)) for r in rows), default=0,
        ) + 1
        rows.append({
            "id": new_id,
            "编排编号": f"RUN_{new_id:04d}",
            "实例编号": snap_id,
            "就绪数量": len(record.ready_ids),
            "跳过数量": len(record.skip_ids),
            "编排轮次": str(round_num),
            "编排时间": snap_id,
            "status": "编排中",
            "pending": True,
            "abnormal": len(record.skip_ids) > 0,
            "skip_reasons": record.skip_reasons,
        })