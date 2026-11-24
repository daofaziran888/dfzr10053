"""跳过审计领域服务：跳过记录追踪、影响范围分析与审计状态管理。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class SkipAuditService(BaseModuleService):
    MODULE = "skip_audit"
    ENTITY = "审计明细"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["审计编号", "实例编号", "跳过原因", "审批人", "影响范围", "审计时间"]
    REQUIRED_FIELDS = ["审计编号", "实例编号", "跳过原因"]
    STATUS_ORDER = ["已采集", "复核中", "已通过", "已驳回"]
    ACTION_RULES = {"提交复核": "复核中", "通过审计": "已通过", "驳回跳过": "已驳回"}
    NEGATIVE_ACTIONS = ["驳回跳过"]

    def pending_review(self) -> list[dict[str, Any]]:
        """获取复核中的审计明细。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "复核中"
        ]

    def audits_for_instance(self, instance_id: str) -> list[dict[str, Any]]:
        """获取指定实例的审计记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if str(r.get("实例编号", "")) == instance_id
        ]

    def rejected_audits(self) -> list[dict[str, Any]]:
        """获取已驳回的审计记录。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已驳回"
        ]

    def impact_contains(self, audit_id: str, instance_id: str) -> bool:
        """检查审计明细的影响范围是否包含指定实例。"""
        for r in store.rows(self.MODULE):
            if r.get("审计编号") == audit_id:
                impact = str(r.get("影响范围", ""))
                return instance_id in impact
        return False