"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class PropagationTraceService(BaseModuleService):
    MODULE = "propagation_trace"
    ENTITY = "追踪明细"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["追踪编号", "补数编号", "传播路径", "受影响实例", "追踪深度", "生成时间"]
    REQUIRED_FIELDS = ["追踪编号", "补数编号", "传播路径"]
    STATUS_ORDER = ["追踪中", "待确认", "已确认", "路径存疑"]
    ACTION_RULES = {"提交确认": "待确认", "确认路径": "已确认", "登记存疑": "路径存疑"}
    NEGATIVE_ACTIONS = []
