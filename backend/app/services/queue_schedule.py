"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class QueueScheduleService(BaseModuleService):
    MODULE = "queue_schedule"
    ENTITY = "调度记录"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["调度编号", "队列标识", "调度轮次", "准入数量", "拒绝数量", "调度时间"]
    REQUIRED_FIELDS = ["调度编号", "队列标识", "调度轮次"]
    STATUS_ORDER = ["调度中", "待复核", "已完成", "调度异常"]
    ACTION_RULES = {"提交复核": "待复核", "确认完成": "已完成", "登记异常": "调度异常"}
    NEGATIVE_ACTIONS = []
