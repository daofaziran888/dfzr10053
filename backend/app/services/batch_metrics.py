"""批次指标·聚合管理，产出指标快照数据集。

领域方法：指标对比、趋势分析和健康度评分。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class BatchMetricsService(BaseModuleService):
    MODULE = "batch_metrics"
    ENTITY = "指标快照"
    OPERATION_TERM = "调度"
    LIST_FIELDS = ["快照编号", "统计日期", "实例成功率", "平均延迟", "补数完成率", "快照时间"]
    REQUIRED_FIELDS = ["快照编号", "统计日期", "实例成功率"]
    STATUS_ORDER = ["已生成", "待复核", "已复核", "已发布"]
    ACTION_RULES = {"提交复核": "待复核", "确认复核": "已复核", "发布快照": "已发布"}
    NEGATIVE_ACTIONS = []

    def latest_snapshot(self) -> dict[str, Any] | None:
        """获取最新已发布的指标快照。"""
        published = [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已发布"
        ]
        if not published:
            return None
        return max(published, key=lambda r: str(r.get("统计日期", "")))

    def snapshot_for_date(self, stat_date: str) -> dict[str, Any] | None:
        """获取指定统计日期的快照。"""
        for r in store.rows(self.MODULE):
            if str(r.get("统计日期", "")) == stat_date:
                return r
        return None

    def success_rate_trend(self) -> list[float]:
        """按日期排序返回成功率序列。"""
        rows = sorted(
            store.rows(self.MODULE),
            key=lambda r: str(r.get("统计日期", "")),
        )
        trends: list[float] = []
        for r in rows:
            try:
                trends.append(float(r.get("实例成功率", "0")))
            except ValueError:
                trends.append(0.0)
        return trends

    def worst_success_rate_date(self) -> tuple[str, float]:
        """返回成功率最低的日期和值。"""
        rows = store.rows(self.MODULE)
        if not rows:
            return "", 1.0
        worst = min(rows, key=lambda r: float(r.get("实例成功率", "1")))
        return (
            str(worst.get("统计日期", "")),
            float(worst.get("实例成功率", "1")),
        )

    def health_summary(self) -> dict[str, Any]:
        """综合健康度汇总。"""
        latest = self.latest_snapshot()
        if not latest:
            return {"status": "无数据"}
        rate = float(latest.get("实例成功率", "0"))
        backfill_rate = float(latest.get("补数完成率", "0"))
        health = "健康" if rate >= 0.95 else ("关注" if rate >= 0.80 else "告警")
        return {
            "date": latest.get("统计日期"),
            "success_rate": rate,
            "backfill_complete_rate": backfill_rate,
            "health": health,
        }