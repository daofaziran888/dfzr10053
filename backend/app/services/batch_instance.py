"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BatchInstanceService(BaseModuleService):
    MODULE = "batch_instance"
    ENTITY = "实例单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["实例编号", "批次标识", "业务日期", "计划时间", "实际时间", "执行时长", "实例状态"]
    REQUIRED_FIELDS = ["实例编号", "批次标识", "业务日期"]
    STATUS_ORDER = ["待就绪", "运行中", "已成功", "已失败"]
    ACTION_RULES = {"发起运行": "运行中", "确认成功": "已成功", "登记失败": "已失败"}
    NEGATIVE_ACTIONS = []
