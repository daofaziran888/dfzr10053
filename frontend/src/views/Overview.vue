<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = [{"name": "依赖登记", "created": 0, "pending": 0, "abnormal": 0}, {"name": "批次实例", "created": 0, "pending": 0, "abnormal": 0}, {"name": "DAG快照", "created": 0, "pending": 0, "abnormal": 0}, {"name": "运行编排", "created": 0, "pending": 0, "abnormal": 0}, {"name": "失败重跑", "created": 0, "pending": 0, "abnormal": 0}, {"name": "补数计划", "created": 0, "pending": 0, "abnormal": 0}, {"name": "补数波次", "created": 0, "pending": 0, "abnormal": 0}, {"name": "基线预警", "created": 0, "pending": 0, "abnormal": 0}, {"name": "资源配额", "created": 0, "pending": 0, "abnormal": 0}, {"name": "优先级规则", "created": 0, "pending": 0, "abnormal": 0}, {"name": "冻结窗口", "created": 0, "pending": 0, "abnormal": 0}, {"name": "上游信号", "created": 0, "pending": 0, "abnormal": 0}, {"name": "实例锁", "created": 0, "pending": 0, "abnormal": 0}, {"name": "跳过审计", "created": 0, "pending": 0, "abnormal": 0}, {"name": "运行历史", "created": 0, "pending": 0, "abnormal": 0}, {"name": "传播追踪", "created": 0, "pending": 0, "abnormal": 0}, {"name": "SLA目标", "created": 0, "pending": 0, "abnormal": 0}, {"name": "队列调度", "created": 0, "pending": 0, "abnormal": 0}, {"name": "预演跑", "created": 0, "pending": 0, "abnormal": 0}, {"name": "批次指标", "created": 0, "pending": 0, "abnormal": 0}, {"name": "冲突解决", "created": 0, "pending": 0, "abnormal": 0}, {"name": "归档实例", "created": 0, "pending": 0, "abnormal": 0}]
  }
})
</script>
