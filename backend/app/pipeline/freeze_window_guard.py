"""冻结窗口拦截：冻结期内禁止补数与重跑操作，冲突自动登记。

核心行为：
- 从 freeze_window 读取冻结中的窗口
- 校验补数计划/失败重跑的操作时间是否落入冻结窗口
- 落在窗口内的操作自动拦截并登记冲突解决记录
- 支持按批次精确冻结和全量冻结两种窗口模式
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FreezeCheckResult:
    """冻结检查结果。"""
    window_id: str
    batch: str
    is_frozen: bool
    blocked_action: str
    reason: str


class FreezeWindowGuardEngine:
    """冻结窗口安检引擎。"""

    def __init__(self, store: Any) -> None:
        self._store = store

    def check_operation(
        self, batch: str, action: str, check_time: str = "",
    ) -> dict[str, Any]:
        """检查操作是否在冻结窗口内。"""
        windows = self._store.rows("freeze_window")
        active_windows = [
            w for w in windows
            if w.get("status") == "冻结中"
        ]

        blocked = False
        block_window = None
        for w in active_windows:
            affected_batch = str(w.get("受影响批次", ""))
            # 精确批次或全量
            if affected_batch and affected_batch != "全部" and affected_batch != batch:
                continue

            # 时间判定：操作时间在窗口范围内
            window_start = str(w.get("窗口开始", ""))
            window_end = str(w.get("窗口结束", ""))
            if self._in_window(check_time, window_start, window_end):
                blocked = True
                block_window = w
                break

        if blocked and block_window:
            # 登记冲突解决记录
            resolve_rows = self._store.rows("conflict_resolve")
            new_id = max(
                (int(r.get("id", 0)) for r in resolve_rows), default=0,
            ) + 1
            resolve_rows.append({
                "id": new_id,
                "解决编号": f"CONF_{new_id:04d}",
                "冲突实例": batch,
                "冲突类型": "冻结拦截",
                "解决方案": f"操作 {action} 被冻结窗口 {block_window.get('窗口编号')} 拦截",
                "操作者": "system",
                "解决时间": block_window.get("窗口开始", ""),
                "status": "已发现",
                "pending": True,
                "abnormal": True,
                "freeze_reason": block_window.get("冻结原因", ""),
            })

            return {
                "allowed": False,
                "blocked_by": str(block_window.get("窗口编号", "")),
                "freeze_reason": block_window.get("冻结原因", ""),
                "action": action,
                "batch": batch,
            }

        return {"allowed": True, "batch": batch, "action": action}

    def _in_window(
        self, check: str, start: str, end: str,
    ) -> bool:
        """简单时间判定：日期字符串比较。"""
        if not check or not start or not end:
            return False
        try:
            return start <= check <= end
        except TypeError:
            return False

    def query_active_freezes(self) -> list[dict[str, Any]]:
        """查询全部生效中的冻结窗口。"""
        return [
            w for w in self._store.rows("freeze_window")
            if w.get("status") == "冻结中"
        ]

    def can_rerun(self, batch: str, rerun_time: str) -> bool:
        """判定重跑操作是否可执行。"""
        result = self.check_operation(batch, "重跑", rerun_time)
        return bool(result.get("allowed"))

    def can_backfill(self, batch: str, plan_time: str) -> bool:
        """判定补数操作是否可执行。"""
        result = self.check_operation(batch, "补数", plan_time)
        return bool(result.get("allowed"))