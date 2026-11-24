"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BackfillWaveService(BaseModuleService):
    MODULE = "backfill_wave"
    ENTITY = "波次批次"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["波次编号", "补数编号", "波次序", "实例数量", "完成数量", "生成时间"]
    REQUIRED_FIELDS = ["波次编号", "补数编号", "波次序"]
    STATUS_ORDER = ["待执行", "执行中", "已完成", "部分失败"]
    ACTION_RULES = {"发起执行": "执行中", "确认完成": "已完成", "登记部分失败": "部分失败"}
    NEGATIVE_ACTIONS = []
