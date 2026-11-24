"""上游信号领域服务：就绪判定、超时检测与信号消费状态查询。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class UpstreamSignalService(BaseModuleService):
    MODULE = "upstream_signal"
    ENTITY = "信号记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["信号编号", "上游批次", "业务日期", "信号类型", "到达时间", "消费状态"]
    REQUIRED_FIELDS = ["信号编号", "上游批次", "业务日期"]
    STATUS_ORDER = ["已到达", "待消费", "已消费", "信号超时"]
    ACTION_RULES = {"发起消费": "待消费", "确认消费": "已消费", "登记超时": "信号超时"}
    NEGATIVE_ACTIONS = ["登记超时"]

    def is_consumed(self, upstream_batch: str, biz_date: str) -> bool:
        """检查指定批次的业务日期信号是否已消费。"""
        for r in store.rows(self.MODULE):
            if (str(r.get("上游批次", "")) == upstream_batch
                    and str(r.get("业务日期", "")) == biz_date
                    and r.get("status") == "已消费"):
                return True
        return False

    def pending_signals(self) -> list[dict[str, Any]]:
        """获取所有待消费的信号。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "待消费"
        ]

    def timed_out_signals(self) -> list[dict[str, Any]]:
        """获取所有超时的信号。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "信号超时"
        ]

    def signal_summary(self, biz_date: str) -> dict[str, Any]:
        """按业务日期汇总信号就绪情况。"""
        rows = [
            r for r in store.rows(self.MODULE)
            if str(r.get("业务日期", "")) == biz_date
        ]
        consumed = sum(1 for r in rows if r.get("status") == "已消费")
        return {
            "biz_date": biz_date,
            "total": len(rows),
            "consumed": consumed,
            "ready_ratio": consumed / len(rows) if rows else 0.0,
        }