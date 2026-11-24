"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class InstanceLockService(BaseModuleService):
    MODULE = "instance_lock"
    ENTITY = "锁记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["锁编号", "实例编号", "持有者", "获取时间", "到期时间", "锁状态"]
    REQUIRED_FIELDS = ["锁编号", "实例编号", "持有者"]
    STATUS_ORDER = ["已获取", "续期中", "已释放", "已抢占"]
    ACTION_RULES = {"发起续期": "续期中", "释放锁": "已释放", "抢占锁": "已抢占"}
    NEGATIVE_ACTIONS = []
