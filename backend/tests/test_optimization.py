"""单元测试：优化算法与安全校验（详设 §11）"""
from app.services.optimization import optimize_schedule, validate_safety


def test_optimize_schedule_feasible():
    units = [
        {"id": 1, "unit_name": "1号", "rated_power_kw": 150, "rated_flow": 100},
        {"id": 2, "unit_name": "2号", "rated_power_kw": 180, "rated_flow": 120},
        {"id": 3, "unit_name": "3号", "rated_power_kw": 200, "rated_flow": 150},
    ]
    result = optimize_schedule(units, target_flow=200)
    assert result["feasible"] is True
    assert result["total_flow"] >= 200
    running = [p for p in result["plan"] if p["action"] == "启动"]
    assert len(running) >= 2


def test_optimize_schedule_max_units():
    units = [
        {"id": 1, "unit_name": "1号", "rated_power_kw": 150, "rated_flow": 100},
        {"id": 2, "unit_name": "2号", "rated_power_kw": 180, "rated_flow": 120},
    ]
    result = optimize_schedule(units, target_flow=200, max_units=1)
    running = [p for p in result["plan"] if p["action"] == "启动"]
    assert len(running) <= 1


def test_validate_safety_pass():
    plan = optimize_schedule(
        [{"id": 1, "unit_name": "1号", "rated_power_kw": 150, "rated_flow": 100}],
        target_flow=80,
    )
    safety = validate_safety(plan, {"min_flow": 80, "max_units_running": 2})
    assert safety["passed"] is True


def test_validate_safety_fail_units():
    plan = {"plan": [{"action": "启动", "unit_name": "A", "target_power_kw": 100}], "total_flow": 100}
    safety = validate_safety(plan, {"max_units_running": 0})
    assert safety["passed"] is False


def test_parse_extract_params():
    from app.agents.tool_agent import parse_extract_params

    text = '提取结果：{"station_id": 1, "min_flow": 250, "objective_text": "最小化能耗"}'
    params = parse_extract_params(text)
    assert params is not None
    assert params["min_flow"] == 250
