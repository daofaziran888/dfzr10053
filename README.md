# 承排工坊 · 批次依赖编排与补数传播平台

面向批次依赖登记、实例编排、失败重跑、补数波次传播、基线预警与冻结窗口管理的离线调度平台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/WorkbenchView.vue|tsx  全部模块共享工作台
│   ├── src/data/modules.ts              18个业务模块配置
│   ├── src/api/              统一请求封装
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/resource.py  通用查询/导出/登记/动作接口
│   ├── app/services/<key>.py    每个模块独立领域逻辑
│   ├── app/services/base.py     共享服务骨架
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8010/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5183/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8010`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 依赖登记 | `dep_registry` | 依赖条目 | 依赖编号、下游批次、上游批次 |
| 批次实例 | `batch_instance` | 实例单 | 实例编号、批次标识、业务日期 |
| DAG快照 | `dag_snapshot` | 图快照 | 快照编号、批次标识、节点数量 |
| 运行编排 | `run_orchestrate` | 编排记录 | 编排编号、实例编号、就绪数量 |
| 失败重跑 | `fail_rerun` | 重跑单 | 重跑编号、实例编号、失败环节 |
| 补数计划 | `backfill_plan` | 补数单 | 补数编号、批次标识、业务日期起 |
| 补数波次 | `backfill_wave` | 波次批次 | 波次编号、补数编号、波次序 |
| 基线预警 | `baseline_alarm` | 预警记录 | 预警编号、批次标识、基线时间 |
| 资源配额 | `resource_quota` | 配额条目 | 配额编号、队列标识、并发上限 |
| 优先级规则 | `priority_rule` | 规则条目 | 规则编号、规则名称、匹配条件 |
| 冻结窗口 | `freeze_window` | 窗口条目 | 窗口编号、窗口名称、窗口开始 |
| 上游信号 | `upstream_signal` | 信号记录 | 信号编号、上游批次、业务日期 |
| 实例锁 | `instance_lock` | 锁记录 | 锁编号、实例编号、持有者 |
| 跳过审计 | `skip_audit` | 审计明细 | 审计编号、实例编号、跳过原因 |
| 运行历史 | `run_history` | 历史明细 | 历史编号、实例编号、尝试序号 |
| 传播追踪 | `propagation_trace` | 追踪明细 | 追踪编号、补数编号、传播路径 |
| SLA目标 | `sla_target` | 目标条目 | 目标编号、批次标识、目标完成时间 |
| 队列调度 | `queue_schedule` | 调度记录 | 调度编号、队列标识、调度轮次 |
| 预演跑 | `dry_run` | 预演单 | 预演编号、补数编号、预演范围 |
| 批次指标 | `batch_metrics` | 指标快照 | 快照编号、统计日期、实例成功率 |
| 冲突解决 | `conflict_resolve` | 解决记录 | 解决编号、冲突实例、冲突类型 |
| 归档实例 | `archive_instance` | 归档记录 | 归档编号、实例编号、归档层级 |

## 约定

- 全部模块共享`frontend/src/views/WorkbenchView.vue|tsx`和一套资源路由。
- 每个模块仍保留独立`backend/app/services/<模块>.py`；纯前端保留
  `frontend/src/domain/<模块>.ts`，用于承载真实业务差异并维持36题位容量。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

领域：数据工程
子方向：数仓与数据湖
