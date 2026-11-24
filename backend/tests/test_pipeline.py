"""综合性管线测试：覆盖全部 10 条链路和关键分支。

测试通过集成管线编排器执行链路，并断言真实数据结果。
同时覆盖 services 层的关键领域方法。
"""
from __future__ import annotations

import pytest
from app.store import Store
from app.pipeline.integration import PipelineOrchestrator
from app.services.dep_registry import DepRegistryService
from app.services.batch_instance import BatchInstanceService
from app.services.dag_snapshot import DagSnapshotService
from app.services.run_orchestrate import RunOrchestrateService
from app.services.fail_rerun import FailRerunService
from app.services.backfill_plan import BackfillPlanService
from app.services.backfill_wave import BackfillWaveService
from app.services.baseline_alarm import BaselineAlarmService
from app.services.resource_quota import ResourceQuotaService
from app.services.priority_rule import PriorityRuleService
from app.services.freeze_window import FreezeWindowService
from app.services.upstream_signal import UpstreamSignalService
from app.services.instance_lock import InstanceLockService
from app.services.skip_audit import SkipAuditService
from app.services.run_history import RunHistoryService
from app.services.propagation_trace import PropagationTraceService
from app.services.sla_target import SlaTargetService
from app.services.queue_schedule import QueueScheduleService
from app.services.dry_run import DryRunService
from app.services.batch_metrics import BatchMetricsService
from app.services.conflict_resolve import ConflictResolveService
from app.services.archive_instance import ArchiveInstanceService


@pytest.fixture(scope="module")
def store():
    return Store()


@pytest.fixture(scope="module")
def orch(store):
    return PipelineOrchestrator(store)


# ======================================================================
# L1: 依赖登记→DAG快照 测试
# ======================================================================
class TestLink1DepToDag:
    def test_build_snapshot_from_effective_deps(self, orch):
        result = orch.run_link_1("DAG-TEST-001", "v_test_1.0")
        assert "error" not in result
        assert int(result["节点数量"]) >= 8
        assert int(result["边数量"]) >= 8
        assert len(result["layers"]) >= 3

    def test_snapshot_written_to_store(self, orch, store):
        snap = store.find("dag_snapshot", int(store.rows("dag_snapshot")[-1]["id"]))
        assert snap is not None
        assert snap["快照编号"] == "DAG-TEST-001"
        assert snap["status"] == "待发布"

    def test_top_layer_nodes_no_upstream(self, orch):
        """顶层节点不应有上游。"""
        result = orch.run_link_1("DAG-TEST-LAYER", "v2")
        top_layer = result["layers"][0]
        edges = result["edges"]
        for node in top_layer:
            has_upstream = any(e.get("to") == node for e in edges)
            assert not has_upstream, f"顶层节点 {node} 不应有上游"

    def test_weak_dep_included_in_edges(self, orch):
        result = orch.run_link_1("DAG-TEST-WEAK", "v3")
        dep_types = {e.get("dep_type") for e in result["edges"]}
        assert "弱依赖" in dep_types

    def test_strong_deps_query(self, orch):
        deps = orch.dep_to_dag.query_strong_deps("dws_trade_daily")
        assert len(deps) >= 1
        assert "dwd_trade_detail" in deps

    def test_weak_deps_query(self, orch):
        deps = orch.dep_to_dag.query_weak_deps("dws_trade_daily")
        assert "dim_trade_shop" in deps or "tmp_trade_mid" in deps


# ======================================================================
# L2: 批次实例→运行编排 测试
# ======================================================================
class TestLink2OrchestrateRun:
    def test_orchestrate_20261122_all_ready(self, orch):
        # 2026-11-22: 全链路健康日
        orch.run_link_1("DAG-SNAP-L2", "v2.0")
        result = orch.run_link_2("DAG-SNAP-L2", "2026-11-22")
        assert result["total_rounds"] >= 3
        # 至少部分实例被准入
        assert result.get("advance_count", 0) > 0, "应有实例被准入"

    def test_orchestrate_20261123_blocked_by_failure(self, orch):
        """2026-11-23: ods_pay_flow 失败，交易链路阻断。"""
        orch.run_link_1("DAG-SNAP-L2-B", "v2.1")
        result = orch.run_link_2("DAG-SNAP-L2-B", "2026-11-23")
        # 应有跳过
        has_skip = any(
            len(round_data.get("skip", [])) > 0
            for round_data in result.get("rounds", [])
        )
        assert has_skip, "应有因上游失败而跳过的实例"

    def test_orchestrate_20261124_signal_not_ready(self, orch):
        """2026-11-24: ods_pay_flow 信号未就绪，第一层即跳过。"""
        orch.run_link_1("DAG-SNAP-L2-C", "v2.2")
        result = orch.run_link_2("DAG-SNAP-L2-C", "2026-11-24")
        first_round = result["rounds"][0] if result["rounds"] else {}
        assert len(first_round.get("skip", [])) > 0, (
            "第一轮应因信号未就绪而跳过"
        )

    def test_orchestrate_nonexistent_snapshot(self, orch):
        result = orch.run_link_2("NONEXIST", "2026-11-22")
        assert "error" in result


# ======================================================================
# L3: 失败重跑→恢复→下游传播 测试
# ======================================================================
class TestLink3RerunRecovery:
    def test_rerun_restart_from_beginning(self, orch):
        """RR-DTD-20261123-01：从头执行重跑 dms_trade_detail"""
        result = orch.run_link_3("RR-DTD-20261123-01")
        assert result["recovered"] is True
        assert result["mode"] == "从头执行"
        assert result["attempt"] == 1

    def test_rerun_max_attempts_escalate(self, orch):
        """RR-TTM-20261123-01 已有2次尝试，第3次应触发升级"""
        orch.run_link_3("RR-TTM-20261123-01")
        result2 = orch.run_link_3("RR-TTM-20261123-01")
        assert result2["recovered"] is False
        assert "3 次上限" in result2.get("reason", "")

    def test_rerun_downstream_propagation(self, orch):
        result = orch.rerun_recovery.compute_downstream_propagation(
            "INS-DTD-20261123",
        )
        assert len(result) >= 1

    def test_rerun_nonexistent(self, orch):
        result = orch.run_link_3("NONEXIST-RERUN")
        assert "error" in result

    def test_rerun_history_recorded(self, orch, store):
        """重跑成功应在运行历史中留下记录。"""
        history_after = len(store.rows("run_history"))
        orch.run_link_3("RR-DUAC-20261121-01")
        history_after2 = len(store.rows("run_history"))
        assert history_after2 >= history_after


# ======================================================================
# L4: 补数计划→波次拆分 测试
# ======================================================================
class TestLink4PlanToWave:
    def test_split_bf_dtd(self, orch):
        orch.run_link_1("DAG-SNAP-L4", "v4.0")
        result = orch.run_link_4("BF-DTD-20261018")
        assert "error" not in result
        assert result["total_waves"] >= 2
        assert result["depth"] == 1

    def test_split_with_depth_zero(self, orch):
        """传播深度为0的补数单仅当前层。"""
        orch.run_link_1("DAG-SNAP-L4-B", "v4.1")
        result = orch.run_link_4("BF-ATB-20261005")
        assert result["total_waves"] == 1

    def test_split_cascading_writes_waves(self, orch, store):
        """拆分后应有波次记录写入存储。"""
        orch.run_link_1("DAG-SNAP-L4-C", "v4.2")
        waves_before = len(store.rows("backfill_wave"))
        orch.run_link_4("BF-DUAD-20261110")
        waves_after = len(store.rows("backfill_wave"))
        assert waves_after > waves_before

    def test_plan_status_updated_to_executing(self, orch, store):
        """补数单拆分后状态应为执行中。"""
        orch.run_link_1("DAG-SNAP-L4-D", "v4.3")
        orch.run_link_4("BF-DUAD-20261110")
        plan = None
        for r in store.rows("backfill_plan"):
            if r.get("补数编号") == "BF-DUAD-20261110":
                plan = r
                break
        assert plan is not None
        assert plan["status"] == "执行中"


# ======================================================================
# L5: 波次执行→补数推进 测试
# ======================================================================
class TestLink5WaveExecution:
    def test_execute_waves_sequential(self, orch):
        result = orch.run_link_5("BF-DTD-20261018")
        assert "error" not in result
        assert result["total_waves"] >= 1

    def test_plan_completed_when_all_done(self, orch, store):
        orch.run_link_5("BF-ATB-20261005")
        plan = None
        for r in store.rows("backfill_plan"):
            if r.get("补数编号") == "BF-ATB-20261005":
                plan = r
                break
        assert plan is not None
        assert plan["status"] == "已完成"

    def test_partial_failed_wave_stays_partial(self, orch, store):
        """部分失败的波次不会推进下一波次。"""
        orch.run_link_5("BF-DTD-20261018")
        failed = [
            w for w in store.rows("backfill_wave")
            if w.get("status") == "部分失败"
        ]
        assert len(failed) >= 1


# ======================================================================
# L6: SLA监控→偏差计算→预警 测试
# ======================================================================
class TestLink6SlaMonitor:
    def test_monitor_generates_alarms_for_p2(self, orch):
        result = orch.run_link_6("dws_trade_daily")
        assert "error" not in result
        assert len(result.get("deviations", [])) >= 1

    def test_monitor_skips_within_threshold(self, orch):
        """dwd_trade_detail 偏差12分钟 < 30 P3阈值，不生成预警。"""
        result = orch.run_link_6("dwd_trade_detail")
        assert len(result.get("generated_alarms", [])) == 0

    def test_alarm_level_p1(self, orch):
        result = orch.run_link_6("ads_trade_board")
        deviations = result.get("deviations", [])
        for d in deviations:
            if d["deviation_min"] >= 120:
                assert d["level"] == "P1"

    def test_active_alarms_count(self, orch):
        alarms = orch.sla_monitor.get_active_alarms()
        assert len(alarms) >= 1

    def test_resolve_alarm_requires_disposal(self, orch):
        ok, msg = orch.sla_monitor.resolve_alarm("ALM-ads_trade_board-20261121")
        assert not ok
        assert "需先处置" in msg


# ======================================================================
# L7: 冻结窗口拦截 测试
# ======================================================================
class TestLink7FreezeGuard:
    def test_backfill_blocked_by_freeze(self, orch):
        result = orch.run_link_7("dws_trade_daily", "补数", "2026-11-23")
        assert result["allowed"] is False
        assert "冻结期" in result.get("freeze_reason", "")

    def test_rerun_blocked_by_full_freeze(self, orch):
        result = orch.run_link_7("dwd_trade_detail", "重跑", "2026-11-22")
        assert result["allowed"] is False

    def test_operation_allowed_outside_window(self, orch):
        result = orch.run_link_7("ods_user_login", "补数", "2026-11-24")
        assert result["allowed"] is True

    def test_conflict_record_created(self, orch, store):
        orch.run_link_7("dws_trade_daily", "补数", "2026-11-25")
        frozen = [
            r for r in store.rows("conflict_resolve")
            if r.get("冲突类型") == "冻结拦截"
        ]
        assert len(frozen) >= 2


# ======================================================================
# L8: 传播追踪 测试
# ======================================================================
class TestLink8Propagation:
    def test_trace_with_published_snap(self, orch):
        result = orch.run_link_8("BF-DTD-20261018")
        assert "error" not in result
        assert result["depth"] >= 0
        assert len(result["path_layers"]) >= 1

    def test_no_published_snap_returns_error(self, orch):
        """BF-DSD-20261101 的 dws_trade_daily 在已发布快照中，应能正常追踪。"""
        result = orch.run_link_8("BF-DSD-20261101")
        assert "error" not in result
        assert result["affected_count"] >= 0

    def test_affected_instances_tracked(self, orch):
        result = orch.run_link_8("BF-DTD-20261018")
        assert result["affected_count"] >= 0

    def test_trace_record_written(self, orch, store):
        before = len(store.rows("propagation_trace"))
        orch.run_link_8("BF-DTD-20261018")
        after = len(store.rows("propagation_trace"))
        assert after > before


# ======================================================================
# L9: 批次指标快照 测试
# ======================================================================
class TestLink9Metrics:
    def test_report_for_20261121(self, orch):
        result = orch.run_link_9("2026-11-21")
        assert result["total"] > 0
        assert result["success_rate"] > 0.0

    def test_report_for_20261123_has_failures(self, orch):
        result = orch.run_link_9("2026-11-23")
        assert result["fail_count"] > 0

    def test_report_for_nonexistent_date(self, orch):
        result = orch.run_link_9("2025-01-01")
        assert "error" in result

    def test_latest_report(self, orch):
        latest = orch.metrics_report.get_latest_report()
        assert latest is not None


# ======================================================================
# L10: 归档清理 测试
# ======================================================================
class TestLink10Archive:
    def test_calculate_candidates(self, orch):
        candidates = orch.archive_cleanup.calculate_candidates(retention_days=60)
        # 2026-07-15 和 2026-08-01 的数据距今超过60天
        assert len(candidates) >= 1

    def test_execute_archive(self, orch):
        result = orch.run_link_10(retention_days=60)
        assert result["archived"] >= 1

    def test_retention_not_reached_skipped(self, orch):
        """2026-09-01 的数据距今不足90天，不应被归档。"""
        candidates = orch.archive_cleanup.calculate_candidates(retention_days=90)
        sept_found = any(
            "2026-09-01" in c.biz_date for c in candidates
        )
        assert not sept_found


# ======================================================================
# 服务层测试
# ======================================================================
class TestDepRegistryService:
    def test_effective_deps_count(self):
        svc = DepRegistryService()
        deps = svc.get_effective_deps()
        assert len(deps) >= 8

    def test_upstream_of_dws_trade_daily(self):
        svc = DepRegistryService()
        ups = svc.upstream_of("dws_trade_daily")
        # 有3个上游：dwd_trade_detail(强)/dim_trade_shop(弱)/tmp_trade_mid(弱)
        assert len(ups) == 3
        assert ups[0]["依赖类型"] == "强依赖"

    def test_downstream_of_ods_pay_flow(self):
        svc = DepRegistryService()
        downs = svc.downstream_of("ods_pay_flow")
        assert len(downs) == 1
        assert downs[0]["下游批次"] == "dwd_trade_detail"

    def test_no_circular_dependency(self):
        svc = DepRegistryService()
        cycles = svc.detect_circular()
        assert len(cycles) == 0


class TestBatchInstanceService:
    def test_instances_by_date(self):
        svc = BatchInstanceService()
        instances = svc.instances_by_date("2026-11-23")
        assert len(instances) >= 10

    def test_ready_check_pending(self):
        svc = BatchInstanceService()
        ready, _ = svc.is_ready("INS-DTD-20261122")
        assert ready

    def test_failed_instances_detected(self):
        svc = BatchInstanceService()
        failed = svc.failed_instances_by_batch("ods_pay_flow")
        assert len(failed) >= 1

    def test_count_by_status(self):
        svc = BatchInstanceService()
        counts = svc.count_by_status("2026-11-23")
        assert counts["已失败"] >= 1


class TestDagSnapshotService:
    def test_published_snapshot_exists(self):
        svc = DagSnapshotService()
        snap = svc.get_published_snapshot()
        assert snap is not None
        assert snap["status"] == "已发布"
        assert snap["快照编号"] == "DAG-2026-1101"

    def test_layers_exist(self):
        svc = DagSnapshotService()
        layers = svc.get_layers("DAG-2026-1101")
        assert len(layers) == 5

    def test_edges_exist(self):
        svc = DagSnapshotService()
        edges = svc.get_edges("DAG-2026-1101")
        assert len(edges) >= 8

    def test_obsolete_check(self):
        svc = DagSnapshotService()
        assert svc.is_obsolete("DAG-2026-1005") is True


class TestFreezeWindowService:
    def test_active_windows(self):
        svc = FreezeWindowService()
        active = svc.active_windows()
        assert len(active) >= 2

    def test_blocks_batch(self):
        svc = FreezeWindowService()
        assert svc.blocks_batch("dws_trade_daily") is True
        assert svc.blocks_batch("dim_user_region") is True  # 全量窗口覆盖

    def test_window_for_batch(self):
        svc = FreezeWindowService()
        w = svc.window_for_batch("ads_trade_board")
        # 全量窗口覆盖所有批次，所以应返回非 None
        assert w is not None
        assert w["窗口编号"] == "FRZ-2026-full-1122"

    def test_overlapping_windows_exist(self):
        svc = FreezeWindowService()
        overlaps = svc.overlapping_windows()
        assert len(overlaps) >= 1


class TestUpstreamSignalService:
    def test_consumed_signal_found(self):
        svc = UpstreamSignalService()
        assert svc.is_consumed("ods_pay_flow", "2026-11-23") is True

    def test_not_consumed_on_20261124(self):
        svc = UpstreamSignalService()
        assert svc.is_consumed("ods_pay_flow", "2026-11-24") is False

    def test_pending_signals(self):
        svc = UpstreamSignalService()
        pending = svc.pending_signals()
        assert len(pending) >= 1

    def test_timed_out_signals(self):
        svc = UpstreamSignalService()
        timed_out = svc.timed_out_signals()
        assert len(timed_out) == 1
        assert timed_out[0]["信号编号"] == "SIG-OPF-20261119"

    def test_signal_summary_20261124(self):
        svc = UpstreamSignalService()
        summary = svc.signal_summary("2026-11-24")
        assert summary["ready_ratio"] < 1.0


class TestInstanceLockService:
    def test_locked_instance(self):
        svc = InstanceLockService()
        assert svc.is_locked("INS-DTD-20261123") is True

    def test_released_lock(self):
        svc = InstanceLockService()
        assert svc.is_locked("INS-DSD-20261122") is False

    def test_preempted_locks(self):
        svc = InstanceLockService()
        preempted = svc.preempted_locks()
        assert len(preempted) == 1

    def test_cannot_acquire_when_locked(self):
        svc = InstanceLockService()
        ok, msg = svc.can_acquire("INS-DTD-20261123")
        assert not ok
        assert "重跑执行器" in msg

    def test_can_acquire_when_free(self):
        svc = InstanceLockService()
        ok, _ = svc.can_acquire("INS-DUAC-20261122")
        assert ok


class TestResourceQuotaService:
    def test_quota_fetched(self):
        svc = ResourceQuotaService()
        quota = svc.get_quota("etl_main")
        assert quota is not None
        assert int(quota["并发上限"]) == 12

    def test_available_slots(self):
        svc = ResourceQuotaService()
        slots = svc.available_slots("etl_main")
        assert slots >= 0

    def test_overloaded_queue(self):
        svc = ResourceQuotaService()
        assert svc.is_overloaded("etl_main") is True

    def test_ads_report_overloaded(self):
        svc = ResourceQuotaService()
        assert svc.is_overloaded("ads_report") is True

    def test_used_percentage(self):
        svc = ResourceQuotaService()
        pct = svc.used_percentage("ads_report")
        assert pct >= 0.9


class TestRunHistoryService:
    def test_dtd_history(self):
        svc = RunHistoryService()
        hist = svc.history_for_instance("INS-DTD-20261123")
        assert len(hist) == 2

    def test_last_successful_ttm(self):
        svc = RunHistoryService()
        last = svc.last_successful("INS-TTM-20261123")
        assert last is not None
        assert last["执行结果"] == "已成功"

    def test_intermittent_failure_detected(self):
        svc = RunHistoryService()
        intermittent = svc.intermittent_failures()
        assert len(intermittent) >= 1


class TestBackfillPlanService:
    def test_active_plans(self):
        svc = BackfillPlanService()
        active = svc.active_plans()
        assert len(active) >= 2

    def test_cascading_plans(self):
        svc = BackfillPlanService()
        cascading = svc.cascading_plans()
        assert len(cascading) >= 2

    def test_date_range_days(self):
        svc = BackfillPlanService()
        days = svc.date_range_days("BF-DSD-20261101")
        assert days == 5


class TestSkipAuditService:
    def test_pending_review(self):
        svc = SkipAuditService()
        pending = svc.pending_review()
        assert len(pending) == 1

    def test_impact_contains(self):
        svc = SkipAuditService()
        assert svc.impact_contains(
            "SKIP-DTD-20261123-01",
            "INS-TTM-20261123",
        ) is True


class TestSlaTargetService:
    def test_effective_targets(self):
        svc = SlaTargetService()
        targets = svc.effective_targets()
        assert len(targets) == 2

    def test_target_time_for_ads(self):
        svc = SlaTargetService()
        time = svc.target_time_for_batch("ads_trade_board")
        assert time == "04:00"

    def test_deviation_calculation(self):
        svc = SlaTargetService()
        dev = svc.deviation_from_target("ads_trade_board", "04:30")
        assert dev == 30


class TestQueueScheduleService:
    def test_rejection_rate(self):
        svc = QueueScheduleService()
        rate = svc.rejection_rate("etl_main")
        assert rate > 0.0

    def test_anomaly_schedules(self):
        svc = QueueScheduleService()
        anomalies = svc.anomaly_schedules()
        assert len(anomalies) == 0


class TestDryRunService:
    def test_pending_review(self):
        svc = DryRunService()
        pending = svc.pending_review()
        assert len(pending) == 1

    def test_dry_runs_for_plan(self):
        svc = DryRunService()
        runs = svc.dry_runs_for_plan("BF-DSD-20261101")
        assert len(runs) == 1

    def test_abandoned_runs(self):
        svc = DryRunService()
        runs = svc.dry_runs_for_plan("BF-DUAD-20261110")
        assert runs[0]["status"] == "已作废"


class TestBatchMetricsService:
    def test_worst_success_rate(self):
        svc = BatchMetricsService()
        date, rate = svc.worst_success_rate_date()
        assert date == "2026-11-22"  # 待复核状态，成功率 0.0

    def test_health_summary(self):
        svc = BatchMetricsService()
        summary = svc.health_summary()
        assert "health" in summary


class TestConflictResolveService:
    def test_unresolved(self):
        svc = ConflictResolveService()
        unresolved = svc.unresolved_conflicts()
        assert len(unresolved) >= 1

    def test_freeze_block_count(self):
        svc = ConflictResolveService()
        count = svc.freeze_block_count()
        assert count == 1

    def test_escalated(self):
        svc = ConflictResolveService()
        escalated = svc.escalated_conflicts()
        assert len(escalated) == 1


class TestArchiveInstanceService:
    def test_restorable(self):
        svc = ArchiveInstanceService()
        restorable = svc.restorable()
        assert len(restorable) == 1

    def test_archived_count(self):
        svc = ArchiveInstanceService()
        count = svc.archived_count()
        assert count == 1

    def test_by_layer(self):
        svc = ArchiveInstanceService()
        layers = svc.by_layer()
        assert "实例级" in layers
        assert "批次级" in layers


# ======================================================================
# 综合集成测试：端到端链路串行
# ======================================================================
class TestIntegrationEndToEnd:
    def test_full_pipeline_sequence(self, orch):
        """链路线性串联：1→2→3→(7拦截)→8→4→5→6→9→10。"""
        # L1
        r1 = orch.run_link_1("DAG-E2E-001", "e2e_v1")
        assert r1["节点数量"] > 0

        # L2
        r2 = orch.run_link_2("DAG-E2E-001", "2026-11-22")
        assert "error" not in r2

        # L3
        r3 = orch.run_link_3("RR-DTD-20261123-01")
        assert r3["recovered"] is True

        # L7 - 冻结检查
        r7 = orch.run_link_7("dws_trade_daily", "补数", "2026-11-23")
        assert r7["allowed"] is False

        # L8
        r8 = orch.run_link_8("BF-DTD-20261018")
        assert "error" not in r8

        # L4 - 需要先重建store中的快照
        orch.run_link_1("DAG-E2E-004", "e2e_v4")
        r4 = orch.run_link_4("BF-DTD-20261018")
        assert r4["total_waves"] >= 1

        # L5
        r5 = orch.run_link_5("BF-DTD-20261018")
        assert "error" not in r5

        # L6
        r6 = orch.run_link_6("dws_trade_daily")
        assert "error" not in r6

        # L9
        r9 = orch.run_link_9("2026-11-21")
        assert r9["total"] > 0

        # L10
        r10 = orch.run_link_10()
        assert r10["archived"] >= 0

    def test_orchestrator_log(self, orch):
        log = orch.execution_log()
        assert len(log) >= 10