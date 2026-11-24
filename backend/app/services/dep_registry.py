"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DepRegistryService(BaseModuleService):
    MODULE = "dep_registry"
    ENTITY = "依赖条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["依赖编号", "下游批次", "上游批次", "依赖类型", "生效日期", "登记时间"]
    REQUIRED_FIELDS = ["依赖编号", "下游批次", "上游批次"]
    STATUS_ORDER = ["草稿", "待确认", "已生效", "已失效"]
    ACTION_RULES = {"提交确认": "待确认", "生效依赖": "已生效", "失效依赖": "已失效"}
    NEGATIVE_ACTIONS = []
