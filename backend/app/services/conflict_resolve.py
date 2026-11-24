"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ConflictResolveService(BaseModuleService):
    MODULE = "conflict_resolve"
    ENTITY = "解决记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["解决编号", "冲突实例", "冲突类型", "解决方案", "操作者", "解决时间"]
    REQUIRED_FIELDS = ["解决编号", "冲突实例", "冲突类型"]
    STATUS_ORDER = ["已发现", "处置中", "已解决", "升级处理"]
    ACTION_RULES = {"发起处置": "处置中", "确认解决": "已解决", "升级冲突": "升级处理"}
    NEGATIVE_ACTIONS = []
