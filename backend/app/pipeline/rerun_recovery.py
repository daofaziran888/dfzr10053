"""失败重跑→恢复判定：对已失败实例发起重跑并判定下游传播范围。

核心行为：
- 从 fail_rerun 读取待重跑/重跑中实例
- 区分从头执行与断点续跑两种重跑方式
- 断点续跑需读取运行历史中最近一次成功尝试的起止时间
- 重跑成功后标记已恢复，下游受影响实例排队传播
- 重跑超过3次仍未恢复则升级为人工处置
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RerunTask:
    """重跑任务描述。"""
    rerun_id: str
    instance_id: str
    fail_stage: str
    rerun_mode: str  # 从头执行 / 断点续跑
    attempt: int
    history: list[dict[str, Any]] = field(default_factory=list)


class RerunRecoveryEngine:
    """失败重跑恢复引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store
        self.MAX_ATTEMPTS = 3

    def execute_rerun(self, rerun_id: str) -> dict[str, Any]:
        """对一条重跑单执行恢复判定。"""
        rerun_row = self._find_rerun(rerun_id)
        if not rerun_row:
            return {"error": f"重跑单 {rerun_id} 不存在", "recovered": False}

        instance_id = str(rerun_row.get("实例编号", ""))
        instance = self._find_instance(instance_id)
        if not instance:
            return {"error": f"实例 {instance_id} 不存在", "recovered": False}

        rerun_mode = str(rerun_row.get("重跑方式", "从头执行"))
        attempt = int(rerun_row.get("重跑次数", "0")) + 1
        rerun_row["重跑次数"] = str(attempt)

        # 读取运行历史
        history = self._get_history(instance_id)

        # 断点续跑：定位最近一次成功的尝试
        resume_point = None
        if rerun_mode == "断点续跑":
            for h in reversed(history):
                if h.get("执行结果") == "已成功":
                    resume_point = h.get("结束时间")
                    break

        # 模拟执行：历史中记录本次尝试
        new_history = {
            "id": max(
                (int(r.get("id", 0)) for r in self._store.rows("run_history")),
                default=0,
            ) + 1,
            "历史编号": f"HIST_{instance_id}_{attempt}",
            "实例编号": instance_id,
            "尝试序号": str(attempt),
            "开始时间": str(instance.get("计划时间", "")),
            "结束时间": str(instance.get("实际时间", "")),
            "执行结果": "已成功",
            "status": "已记录",
            "pending": False,
            "abnormal": False,
            "resume_point": resume_point,
            "mode": rerun_mode,
        }
        self._store.rows("run_history").append(new_history)

        # 重跑成功：标记实例已成功、重跑单已恢复
        instance["status"] = "已成功"
        instance["pending"] = False
        instance["abnormal"] = False

        if attempt >= self.MAX_ATTEMPTS:
            # 超限：升级为人工处置
            rerun_row["status"] = "重跑失败"
            rerun_row["pending"] = False
            rerun_row["abnormal"] = True
            return {
                "rerun_id": rerun_id,
                "instance_id": instance_id,
                "recovered": False,
                "attempt": attempt,
                "reason": f"重跑已达 {self.MAX_ATTEMPTS} 次上限，需人工处置",
                "mode": rerun_mode,
                "resume_point": resume_point,
            }

        rerun_row["status"] = "已恢复"
        rerun_row["pending"] = False
        rerun_row["abnormal"] = False

        return {
            "rerun_id": rerun_id,
            "instance_id": instance_id,
            "recovered": True,
            "attempt": attempt,
            "mode": rerun_mode,
            "resume_point": resume_point,
        }

    def compute_downstream_propagation(
        self, instance_id: str,
    ) -> list[str]:
        """计算失败实例恢复后的下游受影响实例列表。"""
        instance = self._find_instance(instance_id)
        if not instance:
            return []

        batch = str(instance.get("批次标识", ""))
        biz_date = str(instance.get("业务日期", ""))

        # 从 DAG 快照找下游
        downstream_batches: set[str] = set()
        for snap in self._store.rows("dag_snapshot"):
            edges = snap.get("edges", [])
            for e in edges:
                if e.get("from") == batch:
                    downstream_batches.add(e.get("to", ""))

        # 找这些下游批次相同业务日期的实例
        affected: list[str] = []
        for inst in self._store.rows("batch_instance"):
            if (str(inst.get("批次标识", "")) in downstream_batches
                    and str(inst.get("业务日期", "")) == biz_date
                    and inst.get("status") != "已成功"):
                affected.append(str(inst.get("实例编号", "")))

        return affected

    def _find_rerun(self, rerun_id: str) -> dict[str, Any] | None:
        for r in self._store.rows("fail_rerun"):
            if r.get("重跑编号") == rerun_id:
                return r
        return None

    def _find_instance(self, instance_id: str) -> dict[str, Any] | None:
        for r in self._store.rows("batch_instance"):
            if r.get("实例编号") == instance_id:
                return r
        return None

    def _get_history(self, instance_id: str) -> list[dict[str, Any]]:
        return [
            r for r in self._store.rows("run_history")
            if r.get("实例编号") == instance_id
        ]