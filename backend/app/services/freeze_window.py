"""冻结窗口·校验管理，产出窗口条目数据集。

领域方法：时间范围校验、拦截判定与窗口重叠检测。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class FreezeWindowService(BaseModuleService):
    MODULE = "freeze_window"
    ENTITY = "窗口条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["窗口编号", "窗口名称", "窗口开始", "窗口结束", "受影响批次", "冻结原因", "登记时间"]
    REQUIRED_FIELDS = ["窗口编号", "窗口名称", "窗口开始"]
    STATUS_ORDER = ["已登记", "待生效", "冻结中", "已解除"]
    ACTION_RULES = {"提交生效": "待生效", "启动冻结": "冻结中", "解除冻结": "已解除"}
    NEGATIVE_ACTIONS = []

    def active_windows(self) -> list[dict[str, Any]]:
        """获取所有冻结中的窗口。"""
        return [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "冻结中"
        ]

    def blocks_batch(self, batch: str) -> bool:
        """判断该批次当前是否被任何冻结窗口覆盖。"""
        active = self.active_windows()
        for w in active:
            affected = str(w.get("受影响批次", ""))
            if affected == "全部" or affected == batch:
                return True
        return False

    def overlapping_windows(self) -> list[tuple[str, str]]:
        """检测重叠的冻结窗口对（同一批次时间重叠）。"""
        active = self.active_windows()
        overlaps: list[tuple[str, str]] = []
        for i, w1 in enumerate(active):
            for j, w2 in enumerate(active):
                if i >= j:
                    continue
                a1 = str(w1.get("受影响批次", ""))
                a2 = str(w2.get("受影响批次", ""))
                if a1 == "全部" or a2 == "全部" or a1 == a2:
                    overlaps.append((
                        str(w1.get("窗口编号", "")),
                        str(w2.get("窗口编号", "")),
                    ))
        return overlaps

    def window_for_batch(self, batch: str) -> dict[str, Any] | None:
        """获取覆盖指定批次的第一个冻结窗口。"""
        for w in self.active_windows():
            affected = str(w.get("受影响批次", ""))
            if affected == "全部" or affected == batch:
                return w
        return None