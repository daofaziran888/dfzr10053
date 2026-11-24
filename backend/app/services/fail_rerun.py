"""失败重跑领域服务：重跑策略判定、重试次数校验与恢复确认。"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class FailRerunService(BaseModuleService):
    MODULE = "fail_rerun"
    ENTITY = "重跑单"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["重跑编号", "实例编号", "失败环节", "重跑方式", "重跑次数", "重跑时间"]
    REQUIRED_FIELDS = ["重跑编号", "实例编号", "失败环节"]
    STATUS_ORDER = ["待重跑", "重跑中", "已恢复", "重跑失败"]
    ACTION_RULES = {"发起重跑": "重跑中", "确认恢复": "已恢复", "登记失败": "重跑失败"}
    NEGATIVE_ACTIONS = ["登记失败"]

    MAX_RETRY = 3

    def pending_reruns(self) -> list[dict[str, Any]]:
        """获取全部待重跑的重跑单。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "待重跑"
        ]

    def rerun_for_instance(self, instance_id: str) -> dict[str, Any] | None:
        """获取指定实例的最新重跑单。"""
        best = None
        for r in store.rows(self.MODULE):
            if r.get("实例编号") == instance_id:
                if best is None or int(r.get("重跑次数", "0")) > int(best.get("重跑次数", "0")):
                    best = r
        return best

    def exceeded_max_retry(self, rerun_id: str) -> bool:
        """检查重跑单是否超过最大重试次数。"""
        for r in store.rows(self.MODULE):
            if r.get("重跑编号") == rerun_id:
                return int(r.get("重跑次数", "0")) >= self.MAX_RETRY
        return False

    def count_by_mode(self) -> dict[str, int]:
        """按重跑方式统计重跑单数量。"""
        rows = store.rows(self.MODULE)
        modes: dict[str, int] = {}
        for r in rows:
            mode = str(r.get("重跑方式", ""))
            modes[mode] = modes.get(mode, 0) + 1
        return modes