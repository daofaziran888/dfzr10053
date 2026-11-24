"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RunHistoryService(BaseModuleService):
    MODULE = "run_history"
    ENTITY = "历史明细"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["历史编号", "实例编号", "尝试序号", "开始时间", "结束时间", "执行结果"]
    REQUIRED_FIELDS = ["历史编号", "实例编号", "尝试序号"]
    STATUS_ORDER = ["已记录", "待归档", "已归档", "存疑中"]
    ACTION_RULES = {"提交归档": "待归档", "确认归档": "已归档", "登记存疑": "存疑中"}
    NEGATIVE_ACTIONS = []
