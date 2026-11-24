"""批次指标快照：按日汇总调度链路健康度指标并写入 batch_metrics。

核心行为：
- 按统计日期汇总全部批次实例的执行结果
- 计算四个核心指标：实例成功率/平均延迟/补数完成率/异常率
- 指标快照写入 batch_metrics 供分析仪表盘展示
- 同一天重复汇总自动覆盖上一次快照
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BatchMetricsReport:
    """批次指标报告。"""
    stat_date: str
    total_instances: int
    success_count: int
    fail_count: int
    success_rate: float
    avg_delay: str
    backfill_complete_rate: float
    abnormal_count: int


class BatchMetricsReportEngine:
    """批次指标计算引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store

    def generate_report(self, stat_date: str) -> dict[str, Any]:
        """按统计日期生成批次指标快照。"""
        instances = self._store.rows("batch_instance")
        backfill_plans = self._store.rows("backfill_plan")
        backfill_waves = self._store.rows("backfill_wave")

        # 筛选统计日期的实例
        date_instances = [
            i for i in instances
            if str(i.get("业务日期", "")) == stat_date
        ]

        total = len(date_instances)
        if total == 0:
            return {"error": f"统计日期 {stat_date} 无实例数据"}

        success = sum(
            1 for i in date_instances if i.get("status") == "已成功"
        )
        failed = sum(
            1 for i in date_instances if i.get("status") == "已失败"
        )
        abnormal = sum(
            1 for i in date_instances if i.get("abnormal")
        )

        success_rate = round(success / total, 4)

        # 计算平均执行时长
        durations: list[int] = []
        for i in date_instances:
            dur = str(i.get("执行时长", "0"))
            try:
                durations.append(int(dur))
            except (ValueError, TypeError):
                durations.append(0)
        avg_duration = (
            sum(durations) // len(durations) if durations else 0
        )

        # 补数完成率
        plan_completed = sum(
            1 for p in backfill_plans
            if p.get("status") == "已完成"
        )
        plan_total = len(backfill_plans)
        complete_rate = round(
            plan_completed / plan_total, 4,
        ) if plan_total > 0 else 0.0

        # 波次完成率
        wave_completed = sum(
            1 for w in backfill_waves
            if w.get("status") == "已完成"
        )
        wave_total = len(backfill_waves)

        report = BatchMetricsReport(
            stat_date=stat_date,
            total_instances=total,
            success_count=success,
            fail_count=failed,
            success_rate=success_rate,
            avg_delay=f"{avg_duration}分钟",
            backfill_complete_rate=complete_rate,
            abnormal_count=abnormal,
        )

        # 写入指标快照
        metrics_rows = self._store.rows("batch_metrics")
        new_id = max(
            (int(r.get("id", 0)) for r in metrics_rows), default=0,
        ) + 1

        # 检查是否已有当日快照，有则覆盖
        existing = None
        for r in metrics_rows:
            if str(r.get("统计日期", "")) == stat_date:
                existing = r
                break

        if existing:
            existing.update({
                "实例成功率": str(success_rate),
                "平均延迟": f"{avg_duration}分钟",
                "补数完成率": str(complete_rate),
                "快照时间": stat_date,
            })
        else:
            metrics_rows.append({
                "id": new_id,
                "快照编号": f"BMTX_{stat_date}",
                "统计日期": stat_date,
                "实例成功率": str(success_rate),
                "平均延迟": f"{avg_duration}分钟",
                "补数完成率": str(complete_rate),
                "快照时间": stat_date,
                "status": "已生成",
                "pending": False,
                "abnormal": abnormal > total * 0.5,
                "total": total,
                "success_count": success,
                "fail_count": failed,
                "wave_metrics": {
                    "completed": wave_completed,
                    "total": wave_total,
                },
            })

        return {
            "stat_date": stat_date,
            "total": total,
            "success_rate": success_rate,
            "avg_delay_min": avg_duration,
            "backfill_complete_rate": complete_rate,
            "abnormal_count": abnormal,
            "fail_count": failed,
        }

    def get_latest_report(self) -> dict[str, Any] | None:
        """获取最近一次指标快照。"""
        rows = self._store.rows("batch_metrics")
        if not rows:
            return None
        return sorted(rows, key=lambda r: str(r.get("统计日期", "")), reverse=True)[0]