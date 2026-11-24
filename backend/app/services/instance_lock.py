"""实例锁·校验管理，产出锁记录数据集。

领域方法：获取、释放、续期与抢占的全生命周期管理。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class InstanceLockService(BaseModuleService):
    MODULE = "instance_lock"
    ENTITY = "锁记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["锁编号", "实例编号", "持有者", "获取时间", "到期时间", "锁状态"]
    REQUIRED_FIELDS = ["锁编号", "实例编号", "持有者"]
    STATUS_ORDER = ["已获取", "续期中", "已释放", "已抢占"]
    ACTION_RULES = {"发起续期": "续期中", "释放锁": "已释放", "抢占锁": "已抢占"}
    NEGATIVE_ACTIONS = ["抢占锁"]

    def is_locked(self, instance_id: str) -> bool:
        """判断实例是否被锁定。"""
        for r in store.rows(self.MODULE):
            if (str(r.get("实例编号", "")) == instance_id
                    and r.get("status") in ("已获取", "续期中")):
                return True
        return False

    def lock_holder(self, instance_id: str) -> str | None:
        """获取锁持有者，未锁定返回 None。"""
        for r in store.rows(self.MODULE):
            if (str(r.get("实例编号", "")) == instance_id
                    and r.get("status") in ("已获取", "续期中")):
                return str(r.get("持有者", ""))
        return None

    def preempted_locks(self) -> list[dict[str, Any]]:
        """获取所有被抢占的锁记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已抢占"
        ]

    def active_locks(self) -> list[dict[str, Any]]:
        """获取所有活跃的锁（已获取+续期中）。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") in ("已获取", "续期中")
        ]

    def can_acquire(self, instance_id: str) -> tuple[bool, str]:
        """判断实例是否可获取新锁。"""
        if self.is_locked(instance_id):
            holder = self.lock_holder(instance_id)
            return False, f"实例 {instance_id} 已被 {holder} 锁定"
        return True, ""