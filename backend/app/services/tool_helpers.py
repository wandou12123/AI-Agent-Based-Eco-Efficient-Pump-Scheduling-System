"""工具 Agent 规则快路径与回复格式化"""
import json
import re
from typing import Any, Callable, Dict, Optional


def parse_schedule_args(text: str) -> dict:
    """从自然语言中提取 station_id、min_flow、objective_text"""
    args: dict = {"objective_text": "最小化能耗"}
    flow_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:m³/h|m3/h|流量)", text, re.I)
    if not flow_m:
        flow_m = re.search(r"流量\s*(\d+(?:\.\d+)?)", text)
    if flow_m:
        args["min_flow"] = float(flow_m.group(1))

    if "东湖" in text:
        args["station_id"] = 1
    elif "西湖" in text:
        args["station_id"] = 2
    elif "城南" in text:
        args["station_id"] = 3
    elif "城北" in text:
        args["station_id"] = 4
    elif "钱塘" in text:
        args["station_id"] = 5
    else:
        sid_m = re.search(r"(\d+)\s*号\s*泵站", text)
        if sid_m:
            args["station_id"] = int(sid_m.group(1))

    if "最大化" in text or "最大流量" in text:
        args["objective_text"] = "最大化流量"
    elif "最小化" in text or "能耗" in text:
        args["objective_text"] = "最小化能耗"

    return args


def format_tool_result(tool_name: str, result: Any) -> str:
    if tool_name == "list_stations":
        if not result:
            return "当前没有配置泵站，请先在「系统配置」中添加。"
        lines = ["**泵站列表：**", ""]
        for s in result:
            lines.append(f"- #{s['id']} **{s['name']}**（{s.get('location') or '未知位置'}）")
        return "\n".join(lines)

    if tool_name == "get_station_units":
        if not result:
            return "该泵站暂无机组数据。"
        lines = ["**机组参数：**", ""]
        for u in result:
            lines.append(
                f"- {u['name']}：额定功率 {u['power']} kW，额定流量 {u['flow']} m³/h"
            )
        return "\n".join(lines)

    if tool_name == "create_and_optimize_schedule":
        tid = result.get("task_id")
        feasible = result.get("feasible")
        status = result.get("status", "unknown")
        energy = result.get("total_energy_kwh", "-")
        expl = (result.get("explanation") or "")[:300]
        lines = [
            f"**调度优化完成**（任务 #{tid}）",
            "",
            f"- 状态：{status}",
            f"- 可行性：{'可行' if feasible else '未完全满足'}",
            f"- 总功率约：{energy} kW",
            "",
            expl or "（大模型解释见调度页方案详情）",
            "",
            f"👉 请前往 **调度优化** 页面查看任务 #{tid} 的完整方案。",
        ]
        return "\n".join(lines)

    return json.dumps(result, ensure_ascii=False, default=str)


async def try_rule_based_reply(
    user_message: str,
    tool_handlers: Dict[str, Callable],
) -> Optional[tuple[str, Optional[int]]]:
    """
    简单指令不经 LLM 直接调工具（答辩兜底）。
    返回 (reply_text, task_id) 或 None。
    """
    msg = user_message.strip()
    if not msg:
        return None

    if ("列出" in msg or "查询" in msg or "所有" in msg) and "泵站" in msg:
        result = await tool_handlers["list_stations"]({})
        return format_tool_result("list_stations", result), None

    if "机组" in msg and ("查看" in msg or "参数" in msg or "号" in msg):
        args = parse_schedule_args(msg)
        sid = args.get("station_id", 1)
        sid_m = re.search(r"(\d+)\s*号", msg)
        if sid_m and "泵站" not in msg:
            sid = int(sid_m.group(1))
        result = await tool_handlers["get_station_units"]({"station_id": sid})
        return format_tool_result("get_station_units", result), None

    optimize_keywords = ("优化", "调度", "创建任务", "执行优化")
    if any(k in msg for k in optimize_keywords) and (
        "流量" in msg or "泵站" in msg or "东湖" in msg or "西湖" in msg
        or "城南" in msg or "城北" in msg or "钱塘" in msg
    ):
        args = parse_schedule_args(msg)
        if "min_flow" not in args:
            args["min_flow"] = 200
        if "create_and_optimize_schedule" not in tool_handlers:
            return None
        result = await tool_handlers["create_and_optimize_schedule"](args)
        return format_tool_result("create_and_optimize_schedule", result), result.get("task_id")

    return None
