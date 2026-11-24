"""基线预警：SLA目标校验→偏差计算→分级预警生成。

核心行为：
- 从 sla_target 读取已生效的批次时效目标
- 遍历对应批次的批次实例，计算实际完成时间与目标的偏差
- 偏差分钟≥阈值的生成预警记录写入 baseline_alarm
- 偏差超限分三级：30min P1/60min P2/120min P3
- 同一批次同一业务日期的重复预警自动去重
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlaDeviation:
    """SLA偏差计算结果。"""
    batch: str
    biz_date: str
    target_time: str
    actual_time: str
    deviation_minutes: int
    level: str  # P1/P2/P3/正常


class BaselineSlaMonitorEngine:
    """基线预警监控引擎。"""

    P1_THRESHOLD = 120
    P2_THRESHOLD = 60
    P3_THRESHOLD = 30

    def __init__(self, store: Any) -> None:
        self._store = store

    def monitor_batch(self, batch: str) -> dict[str, Any]:
        """对指定批次的实例进行SLA偏离监控。"""
        targets = self._store.rows("sla_target")
        instances = self._store.rows("batch_instance")
        alarms = self._store.rows("baseline_alarm")

        # 获取已生效的批次SLA目标
        batch_target = None
        for t in targets:
            if (str(t.get("批次标识", "")) == batch
                    and t.get("status") == "已生效"):
                batch_target = t
                break

        if not batch_target:
            return {"error": f"批次 {batch} 无可用SLA目标", "alarms": []}

        target_time = str(batch_target.get("目标完成时间", ""))
        stat_period = str(batch_target.get("统计周期", "daily"))

        deviations: list[SlaDeviation] = []
        processed_biz_dates: set[str] = set()

        for inst in instances:
            if str(inst.get("批次标识", "")) != batch:
                continue

            biz_date = str(inst.get("业务日期", ""))
            if biz_date in processed_biz_dates:
                continue
            processed_biz_dates.add(biz_date)

            actual_time = str(inst.get("实际时间", ""))
            deviation = self._compute_deviation(target_time, actual_time)

            if deviation < self.P3_THRESHOLD:
                continue

            level = "P1"
            if deviation >= self.P1_THRESHOLD:
                level = "P1"
            elif deviation >= self.P2_THRESHOLD:
                level = "P2"
            else:
                level = "P3"

            deviations.append(SlaDeviation(
                batch=batch,
                biz_date=biz_date,
                target_time=target_time,
                actual_time=actual_time,
                deviation_minutes=deviation,
                level=level,
            ))

        # 去重后生成预警记录
        alarm_ids: list[str] = []
        for dev in deviations:
            dup = False
            for a in alarms:
                if (str(a.get("批次标识", "")) == dev.batch
                        and str(a.get("基线时间", "")) == dev.target_time
                        and str(a.get("预计完成", "")) == dev.biz_date):
                    dup = True
                    break
            if dup:
                continue

            alarm_id = f"ALM_{dev.batch}_{dev.biz_date}"
            alarms.append({
                "id": max(
                    (int(r.get("id", 0)) for r in alarms), default=0,
                ) + 1,
                "预警编号": alarm_id,
                "批次标识": dev.batch,
                "基线时间": dev.target_time,
                "预计完成": dev.biz_date,
                "偏差分钟": str(dev.deviation_minutes),
                "预警级别": dev.level,
                "预警时间": dev.actual_time,
                "status": "已触发",
                "pending": True,
                "abnormal": True,
            })
            alarm_ids.append(alarm_id)

        return {
            "batch": batch,
            "target_time": target_time,
            "deviations": [
                {
                    "biz_date": d.biz_date,
                    "deviation_min": d.deviation_minutes,
                    "level": d.level,
                }
                for d in deviations
            ],
            "generated_alarms": alarm_ids,
        }

    def _compute_deviation(
        self, target: str, actual: str,
    ) -> int:
        """计算偏差：target 为 HH:MM，actual 可能是 'YYYY-MM-DD HH:MM' 或 'HH:MM'。"""
        try:
            # 从 actual 中提取 HH:MM 部分
            actual_time = actual.split(" ")[-1] if " " in actual else actual
            t_h, t_m = (int(p) for p in target.split(":")[:2])
            a_h, a_m = (int(p) for p in actual_time.split(":")[:2])
            target_min = t_h * 60 + t_m
            actual_min = a_h * 60 + a_m
            return max(0, actual_min - target_min)
        except (ValueError, IndexError):
            return 0

    def get_active_alarms(self) -> list[dict[str, Any]]:
        """获取所有未解除的预警。"""
        return [
            a for a in self._store.rows("baseline_alarm")
            if a.get("status") != "已解除"
        ]

    def resolve_alarm(self, alarm_id: str) -> tuple[bool, str]:
        """解除指定预警。"""
        for a in self._store.rows("baseline_alarm"):
            if a.get("预警编号") == alarm_id:
                if a.get("status") == "已处置":
                    a["status"] = "已解除"
                    a["pending"] = False
                    return True, f"预警 {alarm_id} 已解除"
                return False, f"预警 {alarm_id} 状态为 {a.get('status')}，需先处置"
        return False, f"预警 {alarm_id} 不存在"