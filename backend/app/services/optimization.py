"""能效优化引擎：基于约束的机组组合与负荷分配（贪心策略，详设 §6.1）"""
from typing import Dict, List, Optional


def optimize_schedule(
    units: List[Dict],
    target_flow: float,
    max_units: Optional[int] = None,
) -> Dict:
    """
    基于机组额定参数生成启停与流量分配方案；按单位流量功耗优先选择机组。

    步骤：计算 rated_power_kw/rated_flow 升序排序 → 贪心分配流量 → 未选中机组标记停止。

    Args:
        units: 机组列表，含 id/unit_name/rated_power_kw/rated_flow
        target_flow: 目标总流量 (m³/h)
        max_units: 最多运行台数（可选）

    Returns:
        plan 列表、total_energy_kwh、total_flow、feasible 可行性标记
        时间复杂度 O(n log n)
    """
    if not units:
        return {"plan": [], "total_energy_kwh": 0, "total_flow": 0, "feasible": False}

    rated_units = []
    for u in units:
        pwr = float(u.get("rated_power_kw") or 0)
        flw = float(u.get("rated_flow") or 1)
        efficiency = pwr / flw if flw > 0 else 9999
        rated_units.append({**u, "_eff": efficiency, "_pwr": pwr, "_flw": flw})

    rated_units.sort(key=lambda x: x["_eff"])

    selected = []
    remaining_flow = target_flow

    for u in rated_units:
        if remaining_flow <= 0:
            break
        if max_units and len(selected) >= max_units:
            break

        alloc_flow = min(u["_flw"], remaining_flow)
        ratio = alloc_flow / u["_flw"] if u["_flw"] > 0 else 0
        alloc_power = u["_pwr"] * ratio

        selected.append({
            "unit_id": u["id"],
            "unit_name": u.get("unit_name") or u.get("name", ""),
            "action": "启动",
            "target_power_kw": round(alloc_power, 2),
            "target_flow": round(alloc_flow, 2),
        })
        remaining_flow -= alloc_flow

    selected_ids = {s["unit_id"] for s in selected}
    for u in units:
        if u["id"] not in selected_ids:
            selected.append({
                "unit_id": u["id"],
                "unit_name": u.get("unit_name") or u.get("name", ""),
                "action": "停止",
                "target_power_kw": 0,
                "target_flow": 0,
            })

    total_flow = sum(s["target_flow"] for s in selected)
    total_energy = sum(s["target_power_kw"] for s in selected)
    feasible = remaining_flow <= 0

    return {
        "plan": selected,
        "total_energy_kwh": round(total_energy, 2),
        "total_flow": round(total_flow, 2),
        "feasible": feasible,
    }


def validate_safety(plan: Dict, thresholds: Dict) -> Dict:
    """
    执行功率上限、台数上限、最低流量等阈值校验。

    Args:
        plan: optimize_schedule 输出
        thresholds: 约束阈值（max_power_kw/min_flow/max_units_running 等）

    Returns:
        {passed: bool, checks: [{item, passed, detail}, ...]}，复杂度 O(k)
    """
    checks = []
    passed = True

    max_power = thresholds.get("max_power_kw")
    max_total_power = thresholds.get("max_total_power_kw")
    min_flow = thresholds.get("min_flow")
    max_units = thresholds.get("max_units_running")
    min_units = thresholds.get("min_units_running")

    running = [p for p in plan.get("plan", []) if p.get("action") == "启动"]
    total_power = sum(p.get("target_power_kw", 0) for p in running)

    if max_units is not None and len(running) > max_units:
        checks.append({"item": "运行台数", "passed": False, "detail": f"运行{len(running)}台，超过上限{max_units}台"})
        passed = False
    elif min_units is not None and len(running) < min_units:
        checks.append({"item": "最少运行台数", "passed": False, "detail": f"运行{len(running)}台，低于最少{min_units}台"})
        passed = False
    else:
        checks.append({"item": "运行台数", "passed": True, "detail": f"运行{len(running)}台，在允许范围内"})

    if max_total_power is not None and total_power > max_total_power:
        checks.append({"item": "总功率", "passed": False,
                       "detail": f"总功率{round(total_power, 2)}kW超过上限{max_total_power}kW"})
        passed = False
    else:
        checks.append({"item": "总功率", "passed": True,
                       "detail": f"总功率{round(total_power, 2)}kW在允许范围内"})

    for p in running:
        if max_power and p["target_power_kw"] > max_power:
            checks.append({"item": f"{p['unit_name']}功率", "passed": False,
                           "detail": f"功率{p['target_power_kw']}kW超过上限{max_power}kW"})
            passed = False

    if min_flow and plan.get("total_flow", 0) < min_flow:
        checks.append({"item": "最低流量", "passed": False,
                        "detail": f"总流量{plan['total_flow']}m³/h低于最低要求{min_flow}m³/h"})
        passed = False
    else:
        checks.append({"item": "流量要求", "passed": True, "detail": f"总流量{plan.get('total_flow', 0)}m³/h满足要求"})

    return {"passed": passed, "checks": checks}
