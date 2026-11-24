"""示例数据：批次依赖编排与补数传播平台的真实语义种子数据。

数据围绕一条完整的数仓分层链路组织：
  ods_pay_flow / ods_user_login / dim_trade_shop / dim_user_region
    → dwd_trade_detail / dwd_user_action
      → tmp_trade_mid
        → dws_trade_daily / dws_user_active_daily
          → ads_trade_board

业务日期覆盖 2026-11-20 ~ 2026-11-24（编排主战场），
另有 2026-07-15 / 2026-08-01 / 2026-09-01 三档用于归档保留期边界。
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 批次与层级定义（全仓共享的口径）
# ---------------------------------------------------------------------------
BATCH_CODE: dict[str, str] = {
    "ods_pay_flow": "OPF",
    "ods_user_login": "OUL",
    "dim_trade_shop": "DMS",
    "dim_user_region": "DMR",
    "dwd_trade_detail": "DTD",
    "dwd_user_action": "DUAC",
    "tmp_trade_mid": "TTM",
    "dws_trade_daily": "DSD",
    "dws_user_active_daily": "DUAD",
    "ads_trade_board": "ATB",
}

BATCH_OWNER: dict[str, str] = {
    "ods_pay_flow": "数据接入组",
    "ods_user_login": "数据接入组",
    "dim_trade_shop": "维表治理组",
    "dim_user_region": "维表治理组",
    "dwd_trade_detail": "明细建模组",
    "dwd_user_action": "明细建模组",
    "tmp_trade_mid": "明细建模组",
    "dws_trade_daily": "汇总建模组",
    "dws_user_active_daily": "汇总建模组",
    "ads_trade_board": "应用产出组",
}

# 依赖边：(上游, 下游, 依赖类型, 生效日期, 状态)
DEP_EDGES: list[tuple[str, str, str, str, str]] = [
    ("ods_pay_flow", "dwd_trade_detail", "强依赖", "2026-09-01", "已生效"),
    ("ods_user_login", "dwd_user_action", "强依赖", "2026-09-01", "已生效"),
    ("dwd_trade_detail", "tmp_trade_mid", "强依赖", "2026-09-05", "已生效"),
    ("dwd_trade_detail", "dws_trade_daily", "强依赖", "2026-09-05", "已生效"),
    ("dim_trade_shop", "dws_trade_daily", "弱依赖", "2026-09-05", "已生效"),
    ("tmp_trade_mid", "dws_trade_daily", "弱依赖", "2026-09-10", "已生效"),
    ("dwd_user_action", "dws_user_active_daily", "强依赖", "2026-09-08", "已生效"),
    ("dim_user_region", "dws_user_active_daily", "弱依赖", "2026-09-08", "已生效"),
    ("dws_trade_daily", "ads_trade_board", "强依赖", "2026-09-12", "已生效"),
    ("dws_user_active_daily", "ads_trade_board", "强依赖", "2026-09-12", "已生效"),
]

# 拓扑层级：由 DEP_EDGES 推导，作为已发布快照的固化结构
DAG_LAYERS: list[list[str]] = [
    ["dim_trade_shop", "dim_user_region", "ods_pay_flow", "ods_user_login"],
    ["dwd_trade_detail", "dwd_user_action"],
    ["tmp_trade_mid"],
    ["dws_trade_daily", "dws_user_active_daily"],
    ["ads_trade_board"],
]


def _dag_edges_payload() -> list[dict[str, Any]]:
    """把依赖边转成快照内嵌的边载荷。"""
    return [
        {
            "from": up,
            "to": down,
            "dep_type": dep_type,
            "生效日期": eff,
        }
        for up, down, dep_type, eff, status in DEP_EDGES
        if status == "已生效"
    ]


def _inst_id(batch: str, biz_date: str) -> str:
    """实例编号：INS-<批次缩写>-<yyyymmdd>。"""
    return f"INS-{BATCH_CODE[batch]}-{biz_date.replace('-', '')}"


# ---------------------------------------------------------------------------
# 依赖登记
# ---------------------------------------------------------------------------
def _dep_registry_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # 三条非生效态：草稿 / 待确认 / 已失效，驱动编排忽略分支
    extra = [
        ("DEP-2026-0011", "ads_trade_board", "dws_trade_daily", "弱依赖",
         "2026-11-18", "草稿", True, False),
        ("DEP-2026-0012", "dws_trade_daily", "dim_trade_shop", "强依赖",
         "2026-11-19", "待确认", True, True),
        ("DEP-2026-0013", "tmp_trade_mid", "dwd_trade_detail", "弱依赖",
         "2026-08-20", "已失效", False, False),
    ]
    for i, (up, down, dep_type, eff, status) in enumerate(DEP_EDGES, start=1):
        rows.append({
            "id": i,
            "依赖编号": f"DEP-2026-{i:04d}",
            "下游批次": down,
            "上游批次": up,
            "依赖类型": dep_type,
            "生效日期": eff,
            "登记时间": f"{eff} 09:00",
            "责任组": BATCH_OWNER[down],
            "status": status,
            "pending": False,
            "abnormal": False,
        })
    for j, (dep_no, down, up, dep_type, eff, status, pending, abnormal) in enumerate(
        extra, start=len(DEP_EDGES) + 1,
    ):
        rows.append({
            "id": j,
            "依赖编号": dep_no,
            "下游批次": down,
            "上游批次": up,
            "依赖类型": dep_type,
            "生效日期": eff,
            "登记时间": f"{eff} 09:30",
            "责任组": BATCH_OWNER[down],
            "status": status,
            "pending": pending,
            "abnormal": abnormal,
        })
    return rows


# ---------------------------------------------------------------------------
# 批次实例
# ---------------------------------------------------------------------------
# 2026-11-22：全链路健康日，编排应逐层推进
# 2026-11-23：ods_pay_flow 失败日，交易链路整条阻断、用户链路正常
# 2026-11-24：信号未就绪日，ods_pay_flow 待消费导致下游全部跳过
# 2026-11-20 / 2026-11-21：历史已收尾日，供指标与归档对照
_DATE_PLAN: dict[str, dict[str, str]] = {
    "2026-11-20": {b: "已成功" for b in BATCH_CODE},
    "2026-11-21": {b: "已成功" for b in BATCH_CODE},
    "2026-11-22": {b: "待就绪" for b in BATCH_CODE},
    "2026-11-23": {
        "ods_pay_flow": "已失败",
        "ods_user_login": "已成功",
        "dim_trade_shop": "已成功",
        "dim_user_region": "已成功",
        "dwd_trade_detail": "待就绪",
        "dwd_user_action": "待就绪",
        "tmp_trade_mid": "待就绪",
        "dws_trade_daily": "待就绪",
        "dws_user_active_daily": "待就绪",
        "ads_trade_board": "待就绪",
    },
    "2026-11-24": {b: "待就绪" for b in BATCH_CODE},
}

# 计划时间与实际时间：实际时间晚于目标完成时间的用于 SLA 偏差判定
_PLAN_TIME: dict[str, str] = {
    "ods_pay_flow": "00:30",
    "ods_user_login": "00:40",
    "dim_trade_shop": "00:20",
    "dim_user_region": "00:25",
    "dwd_trade_detail": "01:20",
    "dwd_user_action": "01:30",
    "tmp_trade_mid": "02:00",
    "dws_trade_daily": "02:40",
    "dws_user_active_daily": "02:50",
    "ads_trade_board": "03:40",
}

# 各日期的实际完成时间偏移（分钟），用于制造 SLA 偏差分级
_ACTUAL_DELAY: dict[str, dict[str, int]] = {
    "2026-11-20": {
        "dws_trade_daily": 25, "ads_trade_board": 18,
        "dwd_trade_detail": 12, "tmp_trade_mid": 9,
    },
    "2026-11-21": {
        "dws_trade_daily": 95, "ads_trade_board": 140,
        "dwd_trade_detail": 40, "tmp_trade_mid": 55,
    },
}

_DURATION_MIN: dict[str, int] = {
    "ods_pay_flow": 14, "ods_user_login": 9, "dim_trade_shop": 6,
    "dim_user_region": 7, "dwd_trade_detail": 28, "dwd_user_action": 22,
    "tmp_trade_mid": 16, "dws_trade_daily": 34, "dws_user_active_daily": 30,
    "ads_trade_board": 19,
}

# 归档保留期边界：2026-08-01 与 2026-07-15 超 90 天，2026-09-01 未超
_ARCHIVE_DATES: list[tuple[str, str, str]] = [
    ("2026-08-01", "dws_trade_daily", "已成功"),
    ("2026-07-15", "dwd_trade_detail", "已失败"),
    ("2026-09-01", "ads_trade_board", "已成功"),
]


def _shift_hhmm(hhmm: str, minutes: int) -> str:
    """把 HH:MM 平移若干分钟，跨日不进位（仅用于同日偏差表达）。"""
    hour, minute = (int(p) for p in hhmm.split(":"))
    total = hour * 60 + minute + minutes
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def _batch_instance_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    idx = 0
    for biz_date in sorted(_DATE_PLAN):
        for batch, status in _DATE_PLAN[biz_date].items():
            idx += 1
            delay = _ACTUAL_DELAY.get(biz_date, {}).get(batch, 0)
            plan = f"{biz_date} {_PLAN_TIME[batch]}"
            if status == "已成功":
                actual = f"{biz_date} {_shift_hhmm(_PLAN_TIME[batch], delay)}"
                duration = _DURATION_MIN[batch] + delay
            elif status == "已失败":
                actual = f"{biz_date} {_shift_hhmm(_PLAN_TIME[batch], 35)}"
                duration = 35
            else:
                actual = ""
                duration = 0
            rows.append({
                "id": idx,
                "实例编号": _inst_id(batch, biz_date),
                "批次标识": batch,
                "业务日期": biz_date,
                "计划时间": plan,
                "实际时间": actual,
                "执行时长": str(duration),
                "实例状态": status,
                "责任组": BATCH_OWNER[batch],
                "status": status,
                "pending": status in ("待就绪", "运行中"),
                "abnormal": status == "已失败",
            })

    # 归档保留期边界的三档历史实例
    for biz_date, batch, status in _ARCHIVE_DATES:
        idx += 1
        rows.append({
            "id": idx,
            "实例编号": _inst_id(batch, biz_date),
            "批次标识": batch,
            "业务日期": biz_date,
            "计划时间": f"{biz_date} {_PLAN_TIME[batch]}",
            "实际时间": f"{biz_date} {_shift_hhmm(_PLAN_TIME[batch], 8)}",
            "执行时长": str(_DURATION_MIN[batch] + 8),
            "实例状态": status,
            "责任组": BATCH_OWNER[batch],
            "status": status,
            "pending": False,
            "abnormal": status == "已失败",
        })
    return rows


# ---------------------------------------------------------------------------
# DAG 快照
# ---------------------------------------------------------------------------
def _dag_snapshot_rows() -> list[dict[str, Any]]:
    edges = _dag_edges_payload()
    node_names = sorted(BATCH_CODE)
    return [
        {
            "id": 1,
            "快照编号": "DAG-2026-1101",
            "批次标识": "全链路批次组-2026Q4",
            "节点数量": str(len(node_names)),
            "边数量": str(len(edges)),
            "快照时间": "2026-11-01 06:00",
            "版本标记": "v2026.11.01",
            "status": "已发布",
            "pending": False,
            "abnormal": False,
            "edges": edges,
            "layers": DAG_LAYERS,
            "node_names": node_names,
            "发布人": "调度治理组",
        },
        {
            "id": 2,
            "快照编号": "DAG-2026-1118",
            "批次标识": "全链路批次组-2026Q4",
            "节点数量": str(len(node_names)),
            "边数量": str(len(edges) + 1),
            "快照时间": "2026-11-18 06:00",
            "版本标记": "v2026.11.18-rc",
            "status": "待发布",
            "pending": True,
            "abnormal": True,
            "edges": edges + [{
                "from": "dws_trade_daily",
                "to": "ads_trade_board",
                "dep_type": "弱依赖",
                "生效日期": "2026-11-18",
            }],
            "layers": DAG_LAYERS,
            "node_names": node_names,
            "发布人": "调度治理组",
        },
        {
            "id": 3,
            "快照编号": "DAG-2026-1005",
            "批次标识": "全链路批次组-2026Q3",
            "节点数量": "8",
            "边数量": "7",
            "快照时间": "2026-10-05 06:00",
            "版本标记": "v2026.10.05",
            "status": "已作废",
            "pending": False,
            "abnormal": True,
            "edges": [],
            "layers": [],
            "node_names": [],
            "发布人": "调度治理组",
        },
    ]


# ---------------------------------------------------------------------------
# 运行编排
# ---------------------------------------------------------------------------
def _run_orchestrate_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "编排编号": "ORCH-20261121-01",
            "实例编号": "DAG-2026-1101",
            "就绪数量": "10",
            "跳过数量": "0",
            "编排轮次": "5",
            "编排时间": "2026-11-21 00:15",
            "业务日期": "2026-11-21",
            "status": "已完成",
            "pending": False,
            "abnormal": False,
            "skip_reasons": {},
        },
        {
            "id": 2,
            "编排编号": "ORCH-20261123-01",
            "实例编号": "DAG-2026-1101",
            "就绪数量": "4",
            "跳过数量": "5",
            "编排轮次": "3",
            "编排时间": "2026-11-23 00:15",
            "业务日期": "2026-11-23",
            "status": "编排异常",
            "pending": True,
            "abnormal": True,
            "skip_reasons": {
                _inst_id("dwd_trade_detail", "2026-11-23"):
                    f"上游实例 {_inst_id('ods_pay_flow', '2026-11-23')} 已失败",
                _inst_id("tmp_trade_mid", "2026-11-23"):
                    f"上游实例 {_inst_id('dwd_trade_detail', '2026-11-23')} 状态未完成",
                _inst_id("dws_trade_daily", "2026-11-23"):
                    f"上游实例 {_inst_id('dwd_trade_detail', '2026-11-23')} 状态未完成",
                _inst_id("ads_trade_board", "2026-11-23"):
                    f"上游实例 {_inst_id('dws_trade_daily', '2026-11-23')} 状态未完成",
            },
        },
        {
            "id": 3,
            "编排编号": "ORCH-20261124-01",
            "实例编号": "DAG-2026-1101",
            "就绪数量": "0",
            "跳过数量": "1",
            "编排轮次": "1",
            "编排时间": "2026-11-24 00:15",
            "业务日期": "2026-11-24",
            "status": "编排中",
            "pending": True,
            "abnormal": True,
            "skip_reasons": {
                _inst_id("ods_pay_flow", "2026-11-24"):
                    "上游批次 ods_pay_flow 信号未就绪",
            },
        },
    ]


# ---------------------------------------------------------------------------
# 失败重跑
# ---------------------------------------------------------------------------
def _fail_rerun_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "重跑编号": "RR-DTD-20261123-01",
            "实例编号": _inst_id("dwd_trade_detail", "2026-11-23"),
            "失败环节": "源表分区解析",
            "重跑方式": "从头执行",
            "重跑次数": "0",
            "重跑时间": "2026-11-23 08:10",
            "status": "待重跑",
            "pending": True,
            "abnormal": False,
        },
        {
            "id": 2,
            "重跑编号": "RR-TTM-20261123-01",
            "实例编号": _inst_id("tmp_trade_mid", "2026-11-23"),
            "失败环节": "中间表写入超时",
            "重跑方式": "断点续跑",
            "重跑次数": "2",
            "重跑时间": "2026-11-23 11:40",
            "status": "重跑中",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 3,
            "重跑编号": "RR-DUAC-20261121-01",
            "实例编号": _inst_id("dwd_user_action", "2026-11-21"),
            "失败环节": "行为事件去重",
            "重跑方式": "断点续跑",
            "重跑次数": "1",
            "重跑时间": "2026-11-21 09:05",
            "status": "已恢复",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 4,
            "重跑编号": "RR-OPF-20261123-01",
            "实例编号": _inst_id("ods_pay_flow", "2026-11-23"),
            "失败环节": "上游文件缺失",
            "重跑方式": "从头执行",
            "重跑次数": "1",
            "重跑时间": "2026-11-23 06:30",
            "status": "待重跑",
            "pending": True,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 补数计划
# ---------------------------------------------------------------------------
def _backfill_plan_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "补数编号": "BF-DSD-20261101",
            "批次标识": "dws_trade_daily",
            "业务日期起": "2026-11-01",
            "业务日期止": "2026-11-05",
            "传播深度": "2",
            "创建时间": "2026-11-06 10:00",
            "补数原因": "店铺维表口径更正导致汇总指标偏差",
            "status": "待审批",
            "pending": True,
            "abnormal": False,
        },
        {
            "id": 2,
            "补数编号": "BF-DTD-20261018",
            "批次标识": "dwd_trade_detail",
            "业务日期起": "2026-10-18",
            "业务日期止": "2026-10-20",
            "传播深度": "1",
            "创建时间": "2026-10-21 14:20",
            "补数原因": "上游支付流水迟到数据补报",
            "status": "执行中",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 3,
            "补数编号": "BF-ATB-20261005",
            "批次标识": "ads_trade_board",
            "业务日期起": "2026-10-05",
            "业务日期止": "2026-10-05",
            "传播深度": "0",
            "创建时间": "2026-10-06 09:00",
            "补数原因": "看板单日产出缺失，仅补当日不级联",
            "status": "已完成",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 4,
            "补数编号": "BF-DUAD-20261110",
            "批次标识": "dws_user_active_daily",
            "业务日期起": "2026-11-10",
            "业务日期止": "2026-11-12",
            "传播深度": "3",
            "创建时间": "2026-11-13 16:40",
            "补数原因": "地域维表切换版本，需级联重算下游看板",
            "status": "草拟中",
            "pending": True,
            "abnormal": False,
        },
    ]


# ---------------------------------------------------------------------------
# 补数波次
# ---------------------------------------------------------------------------
def _backfill_wave_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "波次编号": "WAVE-BF-DTD-20261018-1",
            "补数编号": "BF-DTD-20261018",
            "波次序": "1",
            "实例数量": "3",
            "完成数量": "3",
            "生成时间": "2026-10-21 15:00",
            "status": "已完成",
            "pending": False,
            "abnormal": False,
            "affected_nodes": ["dwd_trade_detail"],
        },
        {
            "id": 2,
            "波次编号": "WAVE-BF-DTD-20261018-2",
            "补数编号": "BF-DTD-20261018",
            "波次序": "2",
            "实例数量": "6",
            "完成数量": "4",
            "生成时间": "2026-10-21 15:00",
            "status": "部分失败",
            "pending": True,
            "abnormal": True,
            "affected_nodes": ["tmp_trade_mid", "dws_trade_daily"],
        },
        {
            "id": 3,
            "波次编号": "WAVE-BF-DTD-20261018-3",
            "补数编号": "BF-DTD-20261018",
            "波次序": "3",
            "实例数量": "3",
            "完成数量": "0",
            "生成时间": "2026-10-21 15:00",
            "status": "待执行",
            "pending": True,
            "abnormal": False,
            "affected_nodes": ["ads_trade_board"],
        },
        {
            "id": 4,
            "波次编号": "WAVE-BF-ATB-20261005-1",
            "补数编号": "BF-ATB-20261005",
            "波次序": "1",
            "实例数量": "1",
            "完成数量": "1",
            "生成时间": "2026-10-06 09:30",
            "status": "已完成",
            "pending": False,
            "abnormal": False,
            "affected_nodes": ["ads_trade_board"],
        },
    ]


# ---------------------------------------------------------------------------
# 基线预警
# ---------------------------------------------------------------------------
def _baseline_alarm_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "预警编号": "ALM-dws_trade_daily-20261121",
            "批次标识": "dws_trade_daily",
            "基线时间": "03:00",
            "预计完成": "2026-11-21",
            "偏差分钟": "95",
            "预警级别": "P2",
            "预警时间": "2026-11-21 04:35",
            "值班人": "汇总建模组",
            "status": "已处置",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 2,
            "预警编号": "ALM-ads_trade_board-20261121",
            "批次标识": "ads_trade_board",
            "基线时间": "04:00",
            "预计完成": "2026-11-21",
            "偏差分钟": "140",
            "预警级别": "P1",
            "预警时间": "2026-11-21 06:20",
            "值班人": "应用产出组",
            "status": "确认中",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 3,
            "预警编号": "ALM-dws_trade_daily-20261120",
            "批次标识": "dws_trade_daily",
            "基线时间": "03:00",
            "预计完成": "2026-11-20",
            "偏差分钟": "25",
            "预警级别": "P3",
            "预警时间": "2026-11-20 03:25",
            "值班人": "汇总建模组",
            "status": "已解除",
            "pending": False,
            "abnormal": False,
        },
    ]


# ---------------------------------------------------------------------------
# 资源配额
# ---------------------------------------------------------------------------
def _resource_quota_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "配额编号": "QUOTA-etl-main",
            "队列标识": "etl_main",
            "并发上限": "12",
            "占用并发": "11",
            "排队数量": "27",
            "配额周期": "daily",
            "更新时间": "2026-11-24 00:05",
            "status": "已确认",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 2,
            "配额编号": "QUOTA-etl-backfill",
            "队列标识": "etl_backfill",
            "并发上限": "6",
            "占用并发": "2",
            "排队数量": "3",
            "配额周期": "daily",
            "更新时间": "2026-11-24 00:05",
            "status": "计量中",
            "pending": True,
            "abnormal": False,
        },
        {
            "id": 3,
            "配额编号": "QUOTA-ads-report",
            "队列标识": "ads_report",
            "并发上限": "4",
            "占用并发": "4",
            "排队数量": "9",
            "配额周期": "daily",
            "更新时间": "2026-11-23 22:40",
            "status": "待复核",
            "pending": True,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 优先级规则
# ---------------------------------------------------------------------------
def _priority_rule_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "规则编号": "PRIO-baseline-p1",
            "规则名称": "基线P1批次优先准入",
            "匹配条件": "批次标识 in (ads_trade_board,dws_trade_daily)",
            "优先级权重": "90",
            "更新时间": "2026-11-01 10:00",
            "status": "已生效",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 2,
            "规则编号": "PRIO-backfill-low",
            "规则名称": "补数波次让路规则",
            "匹配条件": "补数编号 like BF-%",
            "优先级权重": "30",
            "更新时间": "2026-11-01 10:05",
            "status": "已生效",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 3,
            "规则编号": "PRIO-rerun-mid",
            "规则名称": "失败重跑中位优先",
            "匹配条件": "重跑方式 = 断点续跑",
            "优先级权重": "60",
            "更新时间": "2026-11-15 14:00",
            "status": "待生效",
            "pending": True,
            "abnormal": False,
        },
        {
            "id": 4,
            "规则编号": "PRIO-tmp-deprecated",
            "规则名称": "临时层历史高优先",
            "匹配条件": "批次标识 = tmp_trade_mid",
            "优先级权重": "80",
            "更新时间": "2026-08-01 09:00",
            "status": "已停用",
            "pending": False,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 冻结窗口
# ---------------------------------------------------------------------------
def _freeze_window_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "窗口编号": "FRZ-2026-Q4-release",
            "窗口名称": "四季度发布冻结期",
            "窗口开始": "2026-11-20",
            "窗口结束": "2026-11-26",
            "受影响批次": "dws_trade_daily",
            "冻结原因": "汇总层口径切换发布，冻结期禁止补数与重跑",
            "登记时间": "2026-11-15 11:00",
            "status": "冻结中",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 2,
            "窗口编号": "FRZ-2026-full-1122",
            "窗口名称": "全量链路冻结窗口",
            "窗口开始": "2026-11-22",
            "窗口结束": "2026-11-23",
            "受影响批次": "全部",
            "冻结原因": "集群机房割接，全量批次暂停变更",
            "登记时间": "2026-11-18 16:20",
            "status": "冻结中",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 3,
            "窗口编号": "FRZ-2026-Q3-release",
            "窗口名称": "三季度发布冻结期",
            "窗口开始": "2026-09-25",
            "窗口结束": "2026-09-30",
            "受影响批次": "ads_trade_board",
            "冻结原因": "看板版本发布，窗口已解除",
            "登记时间": "2026-09-20 10:00",
            "status": "已解除",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 4,
            "窗口编号": "FRZ-2026-1201-plan",
            "窗口名称": "十二月预冻结窗口",
            "窗口开始": "2026-12-01",
            "窗口结束": "2026-12-05",
            "受影响批次": "dws_user_active_daily",
            "冻结原因": "年末口径评审预留窗口，尚未生效",
            "登记时间": "2026-11-20 09:30",
            "status": "待生效",
            "pending": True,
            "abnormal": False,
        },
    ]


# ---------------------------------------------------------------------------
# 上游信号
# ---------------------------------------------------------------------------
def _upstream_signal_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_batches = ["ods_pay_flow", "ods_user_login",
                      "dim_trade_shop", "dim_user_region"]
    # 2026-11-20 ~ 2026-11-23：全部已消费
    idx = 0
    for biz_date in ("2026-11-20", "2026-11-21", "2026-11-22", "2026-11-23"):
        for batch in source_batches:
            idx += 1
            rows.append({
                "id": idx,
                "信号编号": f"SIG-{BATCH_CODE[batch]}-{biz_date.replace('-', '')}",
                "上游批次": batch,
                "业务日期": biz_date,
                "信号类型": "分区就绪",
                "到达时间": f"{biz_date} 00:10",
                "消费状态": "已消费",
                "status": "已消费",
                "pending": False,
                "abnormal": False,
            })
    # 2026-11-24：ods_pay_flow 迟到未消费，其余已消费 → 驱动信号未就绪分支
    for batch in source_batches:
        idx += 1
        late = batch == "ods_pay_flow"
        rows.append({
            "id": idx,
            "信号编号": f"SIG-{BATCH_CODE[batch]}-20261124",
            "上游批次": batch,
            "业务日期": "2026-11-24",
            "信号类型": "分区就绪",
            "到达时间": "" if late else "2026-11-24 00:10",
            "消费状态": "待消费" if late else "已消费",
            "status": "待消费" if late else "已消费",
            "pending": late,
            "abnormal": late,
        })
    # 一条超时信号：驱动超时判定分支
    idx += 1
    rows.append({
        "id": idx,
        "信号编号": "SIG-OPF-20261119",
        "上游批次": "ods_pay_flow",
        "业务日期": "2026-11-19",
        "信号类型": "分区就绪",
        "到达时间": "",
        "消费状态": "超时未达",
        "status": "信号超时",
        "pending": False,
        "abnormal": True,
    })
    return rows


# ---------------------------------------------------------------------------
# 实例锁
# ---------------------------------------------------------------------------
def _instance_lock_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "锁编号": "LOCK-DTD-20261123-01",
            "实例编号": _inst_id("dwd_trade_detail", "2026-11-23"),
            "持有者": "重跑执行器",
            "获取时间": "2026-11-23 08:10",
            "到期时间": "2026-11-23 09:10",
            "锁状态": "已获取",
            "status": "已获取",
            "pending": True,
            "abnormal": False,
        },
        {
            "id": 2,
            "锁编号": "LOCK-TTM-20261123-01",
            "实例编号": _inst_id("tmp_trade_mid", "2026-11-23"),
            "持有者": "补数执行器",
            "获取时间": "2026-11-23 11:40",
            "到期时间": "2026-11-23 12:00",
            "锁状态": "续期中",
            "status": "续期中",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 3,
            "锁编号": "LOCK-DSD-20261122-01",
            "实例编号": _inst_id("dws_trade_daily", "2026-11-22"),
            "持有者": "编排调度器",
            "获取时间": "2026-11-22 02:40",
            "到期时间": "2026-11-22 03:40",
            "锁状态": "已释放",
            "status": "已释放",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 4,
            "锁编号": "LOCK-OPF-20261123-01",
            "实例编号": _inst_id("ods_pay_flow", "2026-11-23"),
            "持有者": "值班人工介入",
            "获取时间": "2026-11-23 06:30",
            "到期时间": "2026-11-23 07:30",
            "锁状态": "已抢占",
            "status": "已抢占",
            "pending": False,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 跳过审计
# ---------------------------------------------------------------------------
def _skip_audit_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "审计编号": "SKIP-DTD-20261123-01",
            "实例编号": _inst_id("dwd_trade_detail", "2026-11-23"),
            "跳过原因": "上游支付流水分区缺失，人工决定跳过等待补报",
            "审批人": "明细建模组-值班",
            "影响范围": ",".join([
                _inst_id("tmp_trade_mid", "2026-11-23"),
                _inst_id("dws_trade_daily", "2026-11-23"),
                _inst_id("ads_trade_board", "2026-11-23"),
            ]),
            "审计时间": "2026-11-23 07:50",
            "status": "复核中",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 2,
            "审计编号": "SKIP-DMS-20261121-01",
            "实例编号": _inst_id("dim_trade_shop", "2026-11-21"),
            "跳过原因": "弱依赖维表当日无变更，编排自动跳过",
            "审批人": "系统自动",
            "影响范围": _inst_id("dws_trade_daily", "2026-11-21"),
            "审计时间": "2026-11-21 00:20",
            "status": "已通过",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 3,
            "审计编号": "SKIP-TTM-20261120-01",
            "实例编号": _inst_id("tmp_trade_mid", "2026-11-20"),
            "跳过原因": "临时层重算申请未获批准",
            "审批人": "汇总建模组-值班",
            "影响范围": _inst_id("dws_trade_daily", "2026-11-20"),
            "审计时间": "2026-11-20 03:10",
            "status": "已驳回",
            "pending": False,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 运行历史
# ---------------------------------------------------------------------------
def _run_history_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "历史编号": "HIST-DTD-20261123-1",
            "实例编号": _inst_id("dwd_trade_detail", "2026-11-23"),
            "尝试序号": "1",
            "开始时间": "2026-11-23 01:20",
            "结束时间": "2026-11-23 01:48",
            "执行结果": "已失败",
            "失败环节": "源表分区解析",
            "status": "已记录",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 2,
            "历史编号": "HIST-DTD-20261123-2",
            "实例编号": _inst_id("dwd_trade_detail", "2026-11-23"),
            "尝试序号": "2",
            "开始时间": "2026-11-23 08:10",
            "结束时间": "2026-11-23 08:41",
            "执行结果": "已失败",
            "失败环节": "源表分区解析",
            "status": "存疑中",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 3,
            "历史编号": "HIST-TTM-20261123-1",
            "实例编号": _inst_id("tmp_trade_mid", "2026-11-23"),
            "尝试序号": "1",
            "开始时间": "2026-11-23 11:40",
            "结束时间": "2026-11-23 12:02",
            "执行结果": "已成功",
            "失败环节": "",
            "status": "已记录",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 4,
            "历史编号": "HIST-TTM-20261123-2",
            "实例编号": _inst_id("tmp_trade_mid", "2026-11-23"),
            "尝试序号": "2",
            "开始时间": "2026-11-23 13:05",
            "结束时间": "2026-11-23 13:33",
            "执行结果": "已失败",
            "失败环节": "中间表写入超时",
            "status": "已记录",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 5,
            "历史编号": "HIST-DUAC-20261121-1",
            "实例编号": _inst_id("dwd_user_action", "2026-11-21"),
            "尝试序号": "1",
            "开始时间": "2026-11-21 01:30",
            "结束时间": "2026-11-21 01:55",
            "执行结果": "已失败",
            "失败环节": "行为事件去重",
            "status": "已归档",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 6,
            "历史编号": "HIST-DUAC-20261121-2",
            "实例编号": _inst_id("dwd_user_action", "2026-11-21"),
            "尝试序号": "2",
            "开始时间": "2026-11-21 09:05",
            "结束时间": "2026-11-21 09:26",
            "执行结果": "已成功",
            "失败环节": "",
            "status": "已归档",
            "pending": False,
            "abnormal": False,
        },
    ]


# ---------------------------------------------------------------------------
# 传播追踪
# ---------------------------------------------------------------------------
def _propagation_trace_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "追踪编号": "TRACE-BF-DTD-20261018-1",
            "补数编号": "BF-DTD-20261018",
            "传播路径": "dwd_trade_detail->tmp_trade_mid,dws_trade_daily->ads_trade_board",
            "受影响实例": "9",
            "追踪深度": "2",
            "生成时间": "2026-10-21 14:35",
            "status": "已确认",
            "pending": False,
            "abnormal": False,
            "path_layers": [
                ["dwd_trade_detail"],
                ["tmp_trade_mid", "dws_trade_daily"],
                ["ads_trade_board"],
            ],
        },
        {
            "id": 2,
            "追踪编号": "TRACE-BF-DSD-20261101-1",
            "补数编号": "BF-DSD-20261101",
            "传播路径": "dws_trade_daily->ads_trade_board",
            "受影响实例": "5",
            "追踪深度": "1",
            "生成时间": "2026-11-06 10:15",
            "status": "待确认",
            "pending": True,
            "abnormal": False,
            "path_layers": [["dws_trade_daily"], ["ads_trade_board"]],
        },
        {
            "id": 3,
            "追踪编号": "TRACE-BF-DUAD-20261110-1",
            "补数编号": "BF-DUAD-20261110",
            "传播路径": "",
            "受影响实例": "0",
            "追踪深度": "0",
            "生成时间": "2026-11-13 16:55",
            "status": "路径存疑",
            "pending": True,
            "abnormal": True,
            "path_layers": [],
        },
    ]


# ---------------------------------------------------------------------------
# SLA 目标
# ---------------------------------------------------------------------------
def _sla_target_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "目标编号": "SLA-dws_trade_daily",
            "批次标识": "dws_trade_daily",
            "目标完成时间": "03:00",
            "时效要求": "每日03:00前产出交易日汇总",
            "统计周期": "daily",
            "更新时间": "2026-10-01 09:00",
            "status": "已生效",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 2,
            "目标编号": "SLA-ads_trade_board",
            "批次标识": "ads_trade_board",
            "目标完成时间": "04:00",
            "时效要求": "每日04:00前刷新看板数据",
            "统计周期": "daily",
            "更新时间": "2026-10-01 09:05",
            "status": "已生效",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 3,
            "目标编号": "SLA-dwd_trade_detail",
            "批次标识": "dwd_trade_detail",
            "目标完成时间": "02:00",
            "时效要求": "每日02:00前完成交易明细清洗",
            "统计周期": "daily",
            "更新时间": "2026-11-10 15:00",
            "status": "待生效",
            "pending": True,
            "abnormal": False,
        },
        {
            "id": 4,
            "目标编号": "SLA-tmp_trade_mid-old",
            "批次标识": "tmp_trade_mid",
            "目标完成时间": "02:20",
            "时效要求": "旧版临时层时效，已废止",
            "统计周期": "daily",
            "更新时间": "2026-08-01 09:00",
            "status": "已废止",
            "pending": False,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 队列调度
# ---------------------------------------------------------------------------
def _queue_schedule_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "调度编号": "SCH-etl_main-20261123-01",
            "队列标识": "etl_main",
            "调度轮次": "1",
            "准入数量": "12",
            "拒绝数量": "15",
            "调度时间": "2026-11-23 00:15",
            "拒绝原因": "配额占满，补数波次按PRIO-backfill-low让路",
            "status": "已完成",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 2,
            "调度编号": "SCH-etl_backfill-20261123-01",
            "队列标识": "etl_backfill",
            "调度轮次": "1",
            "准入数量": "4",
            "拒绝数量": "2",
            "调度时间": "2026-11-23 00:20",
            "拒绝原因": "波次内实例数超并发上限",
            "status": "待复核",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 3,
            "调度编号": "SCH-ads_report-20261122-01",
            "队列标识": "ads_report",
            "调度轮次": "2",
            "准入数量": "4",
            "拒绝数量": "0",
            "调度时间": "2026-11-22 03:40",
            "拒绝原因": "",
            "status": "已完成",
            "pending": False,
            "abnormal": False,
        },
    ]


# ---------------------------------------------------------------------------
# 预演跑
# ---------------------------------------------------------------------------
def _dry_run_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "预演编号": "DRY-BF-DSD-20261101-01",
            "补数编号": "BF-DSD-20261101",
            "预演范围": "2026-11-01~2026-11-05 深度2",
            "预计实例数": "15",
            "预计耗时": "210分钟",
            "预演时间": "2026-11-06 10:30",
            "预计波次数": "2",
            "status": "待评审",
            "pending": True,
            "abnormal": False,
        },
        {
            "id": 2,
            "预演编号": "DRY-BF-DTD-20261018-01",
            "补数编号": "BF-DTD-20261018",
            "预演范围": "2026-10-18~2026-10-20 深度1",
            "预计实例数": "12",
            "预计耗时": "165分钟",
            "预演时间": "2026-10-21 14:40",
            "预计波次数": "3",
            "status": "已评审",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 3,
            "预演编号": "DRY-BF-DUAD-20261110-01",
            "补数编号": "BF-DUAD-20261110",
            "预演范围": "2026-11-10~2026-11-12 深度3",
            "预计实例数": "9",
            "预计耗时": "420分钟",
            "预演时间": "2026-11-13 17:10",
            "预计波次数": "4",
            "status": "已作废",
            "pending": False,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 批次指标
# ---------------------------------------------------------------------------
def _batch_metrics_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "快照编号": "BMTX-20261120",
            "统计日期": "2026-11-20",
            "实例成功率": "1.0",
            "平均延迟": "18分钟",
            "补数完成率": "0.5",
            "快照时间": "2026-11-20 23:50",
            "status": "已发布",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 2,
            "快照编号": "BMTX-20261121",
            "统计日期": "2026-11-21",
            "实例成功率": "0.9",
            "平均延迟": "62分钟",
            "补数完成率": "0.5",
            "快照时间": "2026-11-21 23:50",
            "status": "已复核",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 3,
            "快照编号": "BMTX-20261122",
            "统计日期": "2026-11-22",
            "实例成功率": "0.0",
            "平均延迟": "0分钟",
            "补数完成率": "0.5",
            "快照时间": "2026-11-22 23:50",
            "status": "待复核",
            "pending": True,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 冲突解决
# ---------------------------------------------------------------------------
def _conflict_resolve_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "解决编号": "CONF-20261123-01",
            "冲突实例": _inst_id("dwd_trade_detail", "2026-11-23"),
            "冲突类型": "重跑与编排争用",
            "解决方案": "编排让位重跑，重跑完成后重新入队编排",
            "操作者": "明细建模组-值班",
            "解决时间": "2026-11-23 08:15",
            "status": "已解决",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 2,
            "解决编号": "CONF-20261122-01",
            "冲突实例": "dws_trade_daily",
            "冲突类型": "冻结拦截",
            "解决方案": "补数申请被四季度发布冻结期拦截，延后至窗口解除",
            "操作者": "system",
            "解决时间": "2026-11-22 10:00",
            "status": "处置中",
            "pending": True,
            "abnormal": True,
        },
        {
            "id": 3,
            "解决编号": "CONF-20261123-02",
            "冲突实例": _inst_id("tmp_trade_mid", "2026-11-23"),
            "冲突类型": "补数与重跑锁竞争",
            "解决方案": "锁被补数执行器抢占，重跑单转为等待",
            "操作者": "汇总建模组-值班",
            "解决时间": "2026-11-23 12:05",
            "status": "升级处理",
            "pending": True,
            "abnormal": True,
        },
    ]


# ---------------------------------------------------------------------------
# 归档实例
# ---------------------------------------------------------------------------
def _archive_instance_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "归档编号": "ARCH-20260901-01",
            "实例编号": _inst_id("dwd_trade_detail", "2026-07-15"),
            "归档层级": "实例级",
            "归档时间": "2026-09-01 02:00",
            "保留天数": "90",
            "可回取标记": "是",
            "原始状态": "已失败",
            "status": "已归档",
            "pending": False,
            "abnormal": False,
        },
        {
            "id": 2,
            "归档编号": "ARCH-20260901-02",
            "实例编号": _inst_id("dws_trade_daily", "2026-07-15"),
            "归档层级": "实例级",
            "归档时间": "2026-09-01 02:05",
            "保留天数": "90",
            "可回取标记": "否",
            "原始状态": "已成功",
            "status": "已销毁",
            "pending": False,
            "abnormal": True,
        },
        {
            "id": 3,
            "归档编号": "ARCH-20261101-01",
            "实例编号": _inst_id("ads_trade_board", "2026-08-01"),
            "归档层级": "批次级",
            "归档时间": "2026-11-01 02:00",
            "保留天数": "120",
            "可回取标记": "是",
            "原始状态": "已成功",
            "status": "归档中",
            "pending": True,
            "abnormal": False,
        },
    ]


SEED_ROWS: dict[str, list[dict[str, Any]]] = {
    "dep_registry": _dep_registry_rows(),
    "batch_instance": _batch_instance_rows(),
    "dag_snapshot": _dag_snapshot_rows(),
    "run_orchestrate": _run_orchestrate_rows(),
    "fail_rerun": _fail_rerun_rows(),
    "backfill_plan": _backfill_plan_rows(),
    "backfill_wave": _backfill_wave_rows(),
    "baseline_alarm": _baseline_alarm_rows(),
    "resource_quota": _resource_quota_rows(),
    "priority_rule": _priority_rule_rows(),
    "freeze_window": _freeze_window_rows(),
    "upstream_signal": _upstream_signal_rows(),
    "instance_lock": _instance_lock_rows(),
    "skip_audit": _skip_audit_rows(),
    "run_history": _run_history_rows(),
    "propagation_trace": _propagation_trace_rows(),
    "sla_target": _sla_target_rows(),
    "queue_schedule": _queue_schedule_rows(),
    "dry_run": _dry_run_rows(),
    "batch_metrics": _batch_metrics_rows(),
    "conflict_resolve": _conflict_resolve_rows(),
    "archive_instance": _archive_instance_rows(),
}