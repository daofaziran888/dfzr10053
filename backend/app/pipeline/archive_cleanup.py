"""归档清理：过期实例及其日志按保留天数转入归档并记录可回取标记。

核心行为：
- 从 batch_instance 读取超过保留天的已完成/已失败实例
- 将实例标记加入归档记录写入 archive_instance
- 可回取标记决定审计阶段能否还原现场
- 隐藏保留天外实例，但不从内存移除（可回取还原用）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArchiveCandidate:
    """归档候选条目。"""
    instance_id: str
    batch: str
    biz_date: str
    status: str
    age_days: int
    retention_days: int


class ArchiveCleanupEngine:
    """归档清理引擎。"""

    DEFAULT_RETENTION_DAYS = 90

    def __init__(self, store: Any) -> None:
        self._store = store

    def calculate_candidates(
        self, retention_days: int | None = None,
    ) -> list[ArchiveCandidate]:
        """计算待归档实例列表。"""
        if retention_days is None:
            retention_days = self.DEFAULT_RETENTION_DAYS

        instances = self._store.rows("batch_instance")
        candidates: list[ArchiveCandidate] = []
        today = "2026-11-24"

        for inst in instances:
            biz_date = str(inst.get("业务日期", ""))
            age_days = self._day_diff(biz_date, today)

            if age_days > retention_days and inst.get("status") in (
                "已成功", "已失败",
            ):
                candidates.append(ArchiveCandidate(
                    instance_id=str(inst.get("实例编号", "")),
                    batch=str(inst.get("批次标识", "")),
                    biz_date=biz_date,
                    status=str(inst.get("status", "")),
                    age_days=age_days,
                    retention_days=retention_days,
                ))

        return sorted(candidates, key=lambda c: c.age_days, reverse=True)

    def execute_archive(
        self, retention_days: int | None = None,
    ) -> dict[str, Any]:
        """执行归档操作。"""
        candidates = self.calculate_candidates(retention_days)
        if not candidates:
            return {"archived": 0, "candidates": [], "message": "无待归档实例"}

        archive_rows = self._store.rows("archive_instance")
        archived_ids: list[str] = []
        for candidate in candidates:
            new_id = max(
                (int(r.get("id", 0)) for r in archive_rows), default=0,
            ) + 1
            arch_record = {
                "id": new_id,
                "归档编号": f"ARCH_{new_id:04d}",
                "实例编号": candidate.instance_id,
                "归档层级": "实例级",
                "归档时间": "2026-11-24",
                "保留天数": str(candidate.retention_days),
                "可回取标记": "是",
                "status": "已归档",
                "pending": False,
                "abnormal": False,
                "原始状态": candidate.status,
                "业务日期": candidate.biz_date,
            }
            archive_rows.append(arch_record)
            archived_ids.append(candidate.instance_id)

            # 标记原实例为已归档（保留在内存，可回取）
            for inst in self._store.rows("batch_instance"):
                if inst.get("实例编号") == candidate.instance_id:
                    inst["archived"] = True
                    break

        return {
            "archived": len(archived_ids),
            "retention_days": retention_days or self.DEFAULT_RETENTION_DAYS,
            "instance_ids": archived_ids,
            "candidates": [
                {
                    "instance": c.instance_id,
                    "age_days": c.age_days,
                }
                for c in candidates
            ],
        }

    def _day_diff(self, date_str: str, today: str) -> int:
        """简单日期差计算。"""
        try:
            d_parts = date_str.split("-")
            t_parts = today.split("-")
            if len(d_parts) >= 3 and len(t_parts) >= 3:
                d_days = (
                    int(d_parts[0]) * 365
                    + int(d_parts[1]) * 30
                    + int(d_parts[2])
                )
                t_days = (
                    int(t_parts[0]) * 365
                    + int(t_parts[1]) * 30
                    + int(t_parts[2])
                )
                return t_days - d_days
        except (ValueError, IndexError):
            pass
        return 0