"""端到端集成管线编排器：连接全部管线组件的跨模块数据链路。

10 条贯通链路：
1. 依赖登记→DAG快照生成：已生效依赖构建版本化有向无环图快照
2. 批次实例→运行编排：按DAG层级逐轮判定实例就绪状态
3. 失败重跑→恢复判定→下游传播：重跑成功后下游受影响实例排队传播
4. 补数计划→波次拆分：补数单按依赖层级拆分为波次批次
5. 波次执行→补数推进：按波次序串行推进受资源配额限制
6. SLA目标→偏差计算→分级预警：偏差超限生成P1/P2/P3预警
7. 冻结窗口拦截：冻结期内禁止补数与重跑，冲突自动登记
8. 传播追踪：补数在依赖图上的传播路径与受影响实例清单
9. 批次指标快照：按日汇总调度链路健康度
10. 归档清理：过期实例按保留天数转入归档
"""
from __future__ import annotations

from typing import Any

from app.pipeline.dep_to_dag import DepToDagEngine
from app.pipeline.orchestrate_run import OrchestrateRunEngine
from app.pipeline.rerun_recovery import RerunRecoveryEngine
from app.pipeline.backfill_plan_to_wave import PlanToWaveEngine
from app.pipeline.wave_execution import WaveExecutionEngine
from app.pipeline.baseline_sla_monitor import BaselineSlaMonitorEngine
from app.pipeline.freeze_window_guard import FreezeWindowGuardEngine
from app.pipeline.propagation_tracing import PropagationTracingEngine
from app.pipeline.batch_metrics_report import BatchMetricsReportEngine
from app.pipeline.archive_cleanup import ArchiveCleanupEngine


class PipelineOrchestrator:
    """管线编排器：执行 10 条业务链路并记录执行轨迹。"""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.dep_to_dag = DepToDagEngine(store)
        self.orchestrate = OrchestrateRunEngine(store)
        self.rerun_recovery = RerunRecoveryEngine(store)
        self.plan_to_wave = PlanToWaveEngine(store)
        self.wave_exec = WaveExecutionEngine(store)
        self.sla_monitor = BaselineSlaMonitorEngine(store)
        self.freeze_guard = FreezeWindowGuardEngine(store)
        self.prop_trace = PropagationTracingEngine(store)
        self.metrics_report = BatchMetricsReportEngine(store)
        self.archive_cleanup = ArchiveCleanupEngine(store)
        self._execution_log: list[dict[str, Any]] = []

    def run_link_1(self, snap_id: str = "DAG_SNAP_001", version_tag: str = "v1.0") -> dict[str, Any]:
        """链路1：依赖登记→DAG快照。"""
        result = self.dep_to_dag.build_dag_snapshot(snap_id, version_tag)
        self._log("L1", result)
        return result

    def run_link_2(self, snap_id: str, biz_date: str) -> dict[str, Any]:
        """链路2：批次实例→运行编排。"""
        result = self.orchestrate.orchestrate(snap_id, biz_date)
        self._log("L2", result)
        return result

    def run_link_3(self, rerun_id: str) -> dict[str, Any]:
        """链路3：失败重跑→恢复判定→下游传播。"""
        result = self.rerun_recovery.execute_rerun(rerun_id)
        if result.get("recovered"):
            result["downstream"] = self.rerun_recovery.compute_downstream_propagation(
                result.get("instance_id", ""),
            )
        self._log("L3", result)
        return result

    def run_link_4(self, plan_id: str) -> dict[str, Any]:
        """链路4：补数计划→波次拆分。"""
        result = self.plan_to_wave.split_to_waves(plan_id)
        self._log("L4", result)
        return result

    def run_link_5(self, plan_id: str) -> dict[str, Any]:
        """链路5：波次执行→补数推进。"""
        result = self.wave_exec.execute_wave(plan_id)
        self._log("L5", result)
        return result

    def run_link_6(self, batch: str) -> dict[str, Any]:
        """链路6：SLA目标→偏差计算→分级预警。"""
        result = self.sla_monitor.monitor_batch(batch)
        self._log("L6", result)
        return result

    def run_link_7(self, batch: str, action: str, check_time: str = "") -> dict[str, Any]:
        """链路7：冻结窗口拦截。"""
        result = self.freeze_guard.check_operation(batch, action, check_time)
        self._log("L7", result)
        return result

    def run_link_8(self, plan_id: str) -> dict[str, Any]:
        """链路8：传播追踪。"""
        result = self.prop_trace.trace_propagation(plan_id)
        self._log("L8", result)
        return result

    def run_link_9(self, stat_date: str) -> dict[str, Any]:
        """链路9：批次指标快照。"""
        result = self.metrics_report.generate_report(stat_date)
        self._log("L9", result)
        return result

    def run_link_10(self, retention_days: int | None = None) -> dict[str, Any]:
        """链路10：归档清理。"""
        result = self.archive_cleanup.execute_archive(retention_days)
        self._log("L10", result)
        return result

    def _log(self, link: str, result: dict[str, Any]) -> None:
        self._execution_log.append({
            "link": link,
            "ok": "error" not in result,
            "summary": {k: v for k, v in result.items()
                        if k not in ("waves", "rounds", "path_layers", "affected_instances", "candidates")},
        })

    def execution_log(self) -> list[dict[str, Any]]:
        return list(self._execution_log)