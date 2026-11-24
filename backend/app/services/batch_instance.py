"""批次实例领域服务：状态判定、上游校验与日切。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class BatchInstanceService(BaseModuleService):
    MODULE = "batch_instance"
    ENTITY = "实例单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["实例编号", "批次标识", "业务日期", "计划时间", "实际时间", "执行时长", "实例状态"]
    REQUIRED_FIELDS = ["实例编号", "批次标识", "业务日期"]
    STATUS_ORDER = ["待就绪", "运行中", "已成功", "已失败"]
    ACTION_RULES = {"发起运行": "运行中", "确认成功": "已成功", "登记失败": "已失败"}
    NEGATIVE_ACTIONS = ["登记失败"]

    def instances_by_date(self, biz_date: str) -> list[dict[str, Any]]:
        """按业务日期获取全部实例。"""
        return [
            r for r in store.rows(self.MODULE)
            if str(r.get("业务日期", "")) == biz_date
        ]

    def is_ready(self, instance_id: str) -> tuple[bool, str]:
        """判定实例是否就绪可编排。"""
        inst = store.find(self.MODULE, self._find_id(instance_id))
        if not inst:
            return False, f"实例 {instance_id} 不存在"
        if inst.get("status") != "待就绪":
            return False, f"实例 {instance_id} 当前状态 {inst.get('status')} 不可编排"
        # 检查锁状态
        for lock in store.rows("instance_lock"):
            if (lock.get("实例编号") == instance_id
                    and lock.get("status") == "已获取"):
                return False, f"实例 {instance_id} 被 {lock.get('持有者')} 锁定"
        return True, ""

    def failed_instances_by_batch(self, batch: str) -> list[dict[str, Any]]:
        """查找指定批次下全部已失败实例。"""
        return [
            r for r in store.rows(self.MODULE)
            if str(r.get("批次标识", "")) == batch
            and r.get("status") == "已失败"
        ]

    def count_by_status(self, biz_date: str) -> dict[str, int]:
        """按状态统计指定日期的实例数量。"""
        instances = self.instances_by_date(biz_date)
        result: dict[str, int] = {}
        for s in self.STATUS_ORDER:
            result[s] = sum(1 for i in instances if i.get("status") == s)
        return result

    def _find_id(self, instance_id: str) -> int:
        for r in store.rows(self.MODULE):
            if str(r.get("实例编号", "")) == instance_id:
                return int(r.get("id", 0))
        return 0