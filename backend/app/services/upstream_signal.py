"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class UpstreamSignalService(BaseModuleService):
    MODULE = "upstream_signal"
    ENTITY = "信号记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["信号编号", "上游批次", "业务日期", "信号类型", "到达时间", "消费状态"]
    REQUIRED_FIELDS = ["信号编号", "上游批次", "业务日期"]
    STATUS_ORDER = ["已到达", "待消费", "已消费", "信号超时"]
    ACTION_RULES = {"发起消费": "待消费", "确认消费": "已消费", "登记超时": "信号超时"}
    NEGATIVE_ACTIONS = []
