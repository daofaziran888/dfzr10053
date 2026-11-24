"""运行历史领域服务：尝试序列查询、失败模式分析与间歇故障检测。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class RunHistoryService(BaseModuleService):
    MODULE = "run_history"
    ENTITY = "历史明细"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["历史编号", "实例编号", "尝试序号", "开始时间", "结束时间", "执行结果"]
    REQUIRED_FIELDS = ["历史编号", "实例编号", "尝试序号"]
    STATUS_ORDER = ["已记录", "待归档", "已归档", "存疑中"]
    ACTION_RULES = {"提交归档": "待归档", "确认归档": "已归档", "登记存疑": "存疑中"}
    NEGATIVE_ACTIONS = ["登记存疑"]

    def history_for_instance(self, instance_id: str) -> list[dict[str, Any]]:
        """获取指定实例的完整运行历史，按尝试序号排序。"""
        rows = [
            r for r in store.rows(self.MODULE)
            if str(r.get("实例编号", "")) == instance_id
        ]
        rows.sort(key=lambda r: int(r.get("尝试序号", "0")))
        return rows

    def last_successful(self, instance_id: str) -> dict[str, Any] | None:
        """获取指定实例最近一次成功的运行记录。"""
        rows = self.history_for_instance(instance_id)
        for r in reversed(rows):
            if r.get("执行结果") == "已成功":
                return r
        return None

    def intermittent_failures(self) -> list[dict[str, Any]]:
        """检测间歇性失败：成功之后又有失败的实例。"""
        by_instance: dict[str, list[dict[str, Any]]] = {}
        for r in store.rows(self.MODULE):
            by_instance.setdefault(str(r.get("实例编号", "")), []).append(r)

        result: list[dict[str, Any]] = []
        for inst_id, rows in by_instance.items():
            has_success = any(r.get("执行结果") == "已成功" for r in rows)
            has_failure = any(
                r.get("执行结果") == "已失败"
                for r in rows
                if r.get("status") != "已归档"
            )
            if has_success and has_failure:
                result.append({
                    "instance_id": inst_id,
                    "attempts": len(rows),
                    "last_result": rows[-1].get("执行结果"),
                })
        return result