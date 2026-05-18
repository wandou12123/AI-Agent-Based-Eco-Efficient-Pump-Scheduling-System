"""能效优化引擎：基于约束的机组组合与负荷分配（贪心策略）"""
from typing import List, Dict, Optional
from decimal import Decimal


def optimize_schedule(
    units: List[Dict],
    target_flow: float,
    max_units: Optional[int] = None,
) -> Dict:
    """
    贪心优化：按效率从高到低选择机组，在满足流量约束下最小化能耗。
    units: [{"id":1, "name":"1号机组", "rated_power_kw":150, "rated_flow":100, "meta_json":{...}}]
    target_flow: 目标总流量 (m³/h)
    max_units: 最多运行台数（可选）
    """
    if not units:
        return {"plan": [], "total_energy_kwh": 0, "total_flow": 0, "feasible": False}

    # 按单位流量功耗排序（功耗低 = 效率高）
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

    # 未选中的机组设为停止
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
    """基于规则的安全校验"""
    checks = []
    passed = True

    max_power = thresholds.get("max_power_kw")
    min_flow = thresholds.get("min_flow")
    max_units = thresholds.get("max_units_running")

    running = [p for p in plan.get("plan", []) if p.get("action") == "启动"]

    if max_units and len(running) > max_units:
        checks.append({"item": "运行台数", "passed": False, "detail": f"运行{len(running)}台，超过上限{max_units}台"})
        passed = False
    else:
        checks.append({"item": "运行台数", "passed": True, "detail": f"运行{len(running)}台，在允许范围内"})

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
