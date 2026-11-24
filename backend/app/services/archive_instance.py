"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ArchiveInstanceService(BaseModuleService):
    MODULE = "archive_instance"
    ENTITY = "归档记录"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["归档编号", "实例编号", "归档层级", "归档时间", "保留天数", "可回取标记"]
    REQUIRED_FIELDS = ["归档编号", "实例编号", "归档层级"]
    STATUS_ORDER = ["待归档", "归档中", "已归档", "已销毁"]
    ACTION_RULES = {"发起归档": "归档中", "确认归档": "已归档", "销毁归档": "已销毁"}
    NEGATIVE_ACTIONS = []
