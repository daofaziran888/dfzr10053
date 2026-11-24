"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BackfillPlanService(BaseModuleService):
    MODULE = "backfill_plan"
    ENTITY = "补数单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["补数编号", "批次标识", "业务日期起", "业务日期止", "传播深度", "创建时间"]
    REQUIRED_FIELDS = ["补数编号", "批次标识", "业务日期起"]
    STATUS_ORDER = ["草拟中", "待审批", "执行中", "已完成"]
    ACTION_RULES = {"提交审批": "待审批", "启动补数": "执行中", "确认完成": "已完成"}
    NEGATIVE_ACTIONS = []
