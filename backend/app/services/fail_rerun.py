"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FailRerunService(BaseModuleService):
    MODULE = "fail_rerun"
    ENTITY = "重跑单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["重跑编号", "实例编号", "失败环节", "重跑方式", "重跑次数", "重跑时间"]
    REQUIRED_FIELDS = ["重跑编号", "实例编号", "失败环节"]
    STATUS_ORDER = ["待重跑", "重跑中", "已恢复", "重跑失败"]
    ACTION_RULES = {"发起重跑": "重跑中", "确认恢复": "已恢复", "登记失败": "重跑失败"}
    NEGATIVE_ACTIONS = []
