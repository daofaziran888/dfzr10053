"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BaselineAlarmService(BaseModuleService):
    MODULE = "baseline_alarm"
    ENTITY = "预警记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["预警编号", "批次标识", "基线时间", "预计完成", "偏差分钟", "预警级别", "预警时间"]
    REQUIRED_FIELDS = ["预警编号", "批次标识", "基线时间"]
    STATUS_ORDER = ["已触发", "确认中", "已处置", "已解除"]
    ACTION_RULES = {"提交确认": "确认中", "处置预警": "已处置", "解除预警": "已解除"}
    NEGATIVE_ACTIONS = []
