"""优先级规则·调度管理，产出规则条目数据集。

领域方法：权重排序、条件匹配与准入排队。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class PriorityRuleService(BaseModuleService):
    MODULE = "priority_rule"
    ENTITY = "规则条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["规则编号", "规则名称", "匹配条件", "优先级权重", "更新时间"]
    REQUIRED_FIELDS = ["规则编号", "规则名称", "匹配条件"]
    STATUS_ORDER = ["草稿", "待生效", "已生效", "已停用"]
    ACTION_RULES = {"提交生效": "待生效", "启用规则": "已生效", "停用规则": "已停用"}
    NEGATIVE_ACTIONS = ["停用规则"]

    def effective_rules(self) -> list[dict[str, Any]]:
        """获取所有已生效规则，按权重降序。"""
        rules = [
            r for r in store.rows(self.MODULE)
            if r.get("status") == "已生效"
        ]
        rules.sort(key=lambda r: int(r.get("优先级权重", "0")), reverse=True)
        return rules

    def match_batch(self, batch: str) -> list[dict[str, Any]]:
        """查找匹配指定批次的规则（简单包含匹配）。"""
        rules = self.effective_rules()
        return [
            r for r in rules
            if batch in str(r.get("匹配条件", ""))
        ]

    def highest_weight(self) -> int:
        """获取当前最高优先级权重。"""
        rules = self.effective_rules()
        if not rules:
            return 0
        return max(int(r.get("优先级权重", "0")) for r in rules)

    def rule_count_by_status(self) -> dict[str, int]:
        """按状态统计规则数量。"""
        rows = store.rows(self.MODULE)
        return {
            status: sum(1 for r in rows if r.get("status") == status)
            for status in self.STATUS_ORDER
        }

    def get_rule_by_name(self, name: str) -> dict[str, Any] | None:
        """按规则名称查找。"""
        for r in store.rows(self.MODULE):
            if r.get("规则名称") == name:
                return r
        return None