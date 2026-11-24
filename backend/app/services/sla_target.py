"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SlaTargetService(BaseModuleService):
    MODULE = "sla_target"
    ENTITY = "目标条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["目标编号", "批次标识", "目标完成时间", "时效要求", "统计周期", "更新时间"]
    REQUIRED_FIELDS = ["目标编号", "批次标识", "目标完成时间"]
    STATUS_ORDER = ["草拟中", "待生效", "已生效", "已废止"]
    ACTION_RULES = {"提交生效": "待生效", "生效目标": "已生效", "废止目标": "已废止"}
    NEGATIVE_ACTIONS = []
