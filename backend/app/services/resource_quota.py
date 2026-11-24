"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ResourceQuotaService(BaseModuleService):
    MODULE = "resource_quota"
    ENTITY = "配额条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["配额编号", "队列标识", "并发上限", "占用并发", "排队数量", "配额周期", "更新时间"]
    REQUIRED_FIELDS = ["配额编号", "队列标识", "并发上限"]
    STATUS_ORDER = ["计量中", "待复核", "已确认", "已调整"]
    ACTION_RULES = {"提交复核": "待复核", "确认配额": "已确认", "调整配额": "已调整"}
    NEGATIVE_ACTIONS = []
