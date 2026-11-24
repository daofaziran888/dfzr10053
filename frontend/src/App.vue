<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">承排工坊 · 批次依赖编排与补数传播平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向批次依赖登记、实例编排、失败重跑、补数波次传播、基线预警与冻结窗口管理的离线调度平台。</span>
        <span class="head-user">当前值班：数据工程组</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
const navItems = [{ label: "运营概览", path: "/" }, { label: "依赖登记", path: "/dep_registry" }, { label: "批次实例", path: "/batch_instance" }, { label: "DAG快照", path: "/dag_snapshot" }, { label: "运行编排", path: "/run_orchestrate" }, { label: "失败重跑", path: "/fail_rerun" }, { label: "补数计划", path: "/backfill_plan" }, { label: "补数波次", path: "/backfill_wave" }, { label: "基线预警", path: "/baseline_alarm" }, { label: "资源配额", path: "/resource_quota" }, { label: "优先级规则", path: "/priority_rule" }, { label: "冻结窗口", path: "/freeze_window" }, { label: "上游信号", path: "/upstream_signal" }, { label: "实例锁", path: "/instance_lock" }, { label: "跳过审计", path: "/skip_audit" }, { label: "运行历史", path: "/run_history" }, { label: "传播追踪", path: "/propagation_trace" }, { label: "SLA目标", path: "/sla_target" }, { label: "队列调度", path: "/queue_schedule" }, { label: "预演跑", path: "/dry_run" }, { label: "批次指标", path: "/batch_metrics" }, { label: "冲突解决", path: "/conflict_resolve" }, { label: "归档实例", path: "/archive_instance" }]
</script>
