"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RunOrchestrateService(BaseModuleService):
    MODULE = "run_orchestrate"
    ENTITY = "编排记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["编排编号", "实例编号", "就绪数量", "跳过数量", "编排轮次", "编排时间"]
    REQUIRED_FIELDS = ["编排编号", "实例编号", "就绪数量"]
    STATUS_ORDER = ["编排中", "待复核", "已完成", "编排异常"]
    ACTION_RULES = {"提交复核": "待复核", "确认完成": "已完成", "登记异常": "编排异常"}
    NEGATIVE_ACTIONS = []
