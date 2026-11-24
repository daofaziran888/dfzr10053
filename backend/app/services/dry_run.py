"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DryRunService(BaseModuleService):
    MODULE = "dry_run"
    ENTITY = "预演单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["预演编号", "补数编号", "预演范围", "预计实例数", "预计耗时", "预演时间"]
    REQUIRED_FIELDS = ["预演编号", "补数编号", "预演范围"]
    STATUS_ORDER = ["预演中", "待评审", "已评审", "已作废"]
    ACTION_RULES = {"提交评审": "待评审", "确认评审": "已评审", "作废预演": "已作废"}
    NEGATIVE_ACTIONS = ["作废预演"]
