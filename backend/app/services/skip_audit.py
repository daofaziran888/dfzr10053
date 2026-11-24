"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SkipAuditService(BaseModuleService):
    MODULE = "skip_audit"
    ENTITY = "审计明细"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["审计编号", "实例编号", "跳过原因", "审批人", "影响范围", "审计时间"]
    REQUIRED_FIELDS = ["审计编号", "实例编号", "跳过原因"]
    STATUS_ORDER = ["已采集", "复核中", "已通过", "已驳回"]
    ACTION_RULES = {"提交复核": "复核中", "通过审计": "已通过", "驳回跳过": "已驳回"}
    NEGATIVE_ACTIONS = ["驳回跳过"]
