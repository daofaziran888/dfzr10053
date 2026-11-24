"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DagSnapshotService(BaseModuleService):
    MODULE = "dag_snapshot"
    ENTITY = "图快照"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["快照编号", "批次标识", "节点数量", "边数量", "快照时间", "版本标记"]
    REQUIRED_FIELDS = ["快照编号", "批次标识", "节点数量"]
    STATUS_ORDER = ["生成中", "待发布", "已发布", "已作废"]
    ACTION_RULES = {"提交发布": "待发布", "确认发布": "已发布", "作废快照": "已作废"}
    NEGATIVE_ACTIONS = ["作废快照"]
