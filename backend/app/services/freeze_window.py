"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FreezeWindowService(BaseModuleService):
    MODULE = "freeze_window"
    ENTITY = "窗口条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["窗口编号", "窗口名称", "窗口开始", "窗口结束", "受影响批次", "冻结原因", "登记时间"]
    REQUIRED_FIELDS = ["窗口编号", "窗口名称", "窗口开始"]
    STATUS_ORDER = ["已登记", "待生效", "冻结中", "已解除"]
    ACTION_RULES = {"提交生效": "待生效", "启动冻结": "冻结中", "解除冻结": "已解除"}
    NEGATIVE_ACTIONS = []
