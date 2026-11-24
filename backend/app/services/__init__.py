"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
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

SERVICES: dict[str, BaseModuleService] = {
    "dep_registry": DepRegistryService(),
    "batch_instance": BatchInstanceService(),
    "dag_snapshot": DagSnapshotService(),
    "run_orchestrate": RunOrchestrateService(),
    "fail_rerun": FailRerunService(),
    "backfill_plan": BackfillPlanService(),
    "backfill_wave": BackfillWaveService(),
    "baseline_alarm": BaselineAlarmService(),
    "resource_quota": ResourceQuotaService(),
    "priority_rule": PriorityRuleService(),
    "freeze_window": FreezeWindowService(),
    "upstream_signal": UpstreamSignalService(),
    "instance_lock": InstanceLockService(),
    "skip_audit": SkipAuditService(),
    "run_history": RunHistoryService(),
    "propagation_trace": PropagationTraceService(),
    "sla_target": SlaTargetService(),
    "queue_schedule": QueueScheduleService(),
    "dry_run": DryRunService(),
    "batch_metrics": BatchMetricsService(),
    "conflict_resolve": ConflictResolveService(),
    "archive_instance": ArchiveInstanceService(),
}


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)
