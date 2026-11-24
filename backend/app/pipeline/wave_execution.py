"""补数波次执行：按波次序串行推进波次内实例的补数。

核心行为：
- 从 backfill_wave 读取待执行/执行中波次
- 同波次内实例可并行准入（受资源配额限制）
- 波次完成后推进下一波次
- 部分失败的波次留在部分失败状态并登记冲突
- 全部波次完成后将补数单标记为已完成
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WaveExecuteResult:
    """波次执行结果。"""
    wave_id: str
    wave_order: int
    completed: int
    failed: int
    quota_blocked: int


class WaveExecutionEngine:
    """波次执行与补数推进引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store

    def execute_wave(
        self, plan_id: str,
    ) -> dict[str, Any]:
        """按波次序依次推进补数波次。"""
        waves = sorted(
            [
                w for w in self._store.rows("backfill_wave")
                if w.get("补数编号") == plan_id
            ],
            key=lambda w: int(str(w.get("波次序", "0"))),
        )

        if not waves:
            return {"error": f"补数单 {plan_id} 无可用波次", "results": []}

        # 获取队列配额
        quota = self._get_queue_quota()
        max_concurrent = quota.get("concurrent_limit", 10)

        results: list[WaveExecuteResult] = []
        for wave in waves:
            wave_id = str(wave.get("波次数号", ""))
            wave_order = int(str(wave.get("波次序", "0")))
            affected_nodes = wave.get("affected_nodes", [])
            instance_count = len(affected_nodes)

            if wave.get("status") in ("已完成", "部分失败"):
                continue

            # 检查是否前一波次已完成
            prev_order = wave_order - 1
            if prev_order > 0:
                prev_waves = [
                    w for w in waves
                    if int(str(w.get("波次序", "0"))) == prev_order
                ]
                if prev_waves and prev_waves[0].get("status") != "已完成":
                    # 前一波次未完成，当前波次等待
                    wave["pending"] = True
                    continue

            # 执行当前波次：受配额限制准入
            completed = 0
            failed = 0
            quota_blocked = 0

            for i, node in enumerate(affected_nodes):
                if i < max_concurrent:
                    # 在当前存储数据中找到对应实例并标记处理
                    for inst in self._store.rows("batch_instance"):
                        if str(inst.get("批次标识", "")) == node:
                            if inst.get("status") == "已成功":
                                completed += 1
                            elif inst.get("status") == "已失败":
                                failed += 1
                            break
                else:
                    quota_blocked = instance_count - max_concurrent
                    break

            # 判定波次结果
            if failed > 0:
                wave["status"] = "部分失败"
                wave["abnormal"] = True
                wave["完成数量"] = completed
            else:
                wave["status"] = "已完成"
                wave["pending"] = False
                wave["完成数量"] = completed + max(0, instance_count - failed - quota_blocked)

            wave["执行中"] = False
            results.append(WaveExecuteResult(
                wave_id=wave_id,
                wave_order=wave_order,
                completed=completed,
                failed=failed,
                quota_blocked=quota_blocked,
            ))

        # 检查是否全部完成
        all_done = all(
            w.get("status") in ("已完成", "部分失败")
            for w in waves
        )
        if all_done:
            plan = self._find_plan(plan_id)
            if plan:
                plan["status"] = "已完成"
                plan["pending"] = False

        return {
            "plan_id": plan_id,
            "total_waves": len(waves),
            "results": [
                {
                    "wave": r.wave_id,
                    "order": r.wave_order,
                    "completed": r.completed,
                    "failed": r.failed,
                    "blocked": r.quota_blocked,
                }
                for r in results
            ],
        }

    def _find_plan(self, plan_id: str) -> dict[str, Any] | None:
        for r in self._store.rows("backfill_plan"):
            if r.get("补数编号") == plan_id:
                return r
        return None

    def _get_queue_quota(self) -> dict[str, Any]:
        quotas = self._store.rows("resource_quota")
        if quotas:
            return {
                "concurrent_limit": int(quotas[0].get("并发上限", "10")),
                "used": int(quotas[0].get("占用并发", "0")),
                "queued": int(quotas[0].get("排队数量", "0")),
            }
        return {"concurrent_limit": 10, "used": 0, "queued": 0}