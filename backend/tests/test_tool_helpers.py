"""单元测试：工具 Agent 规则快路径与回复格式化"""
import pytest

from app.services.tool_helpers import parse_schedule_args, format_tool_result, try_rule_based_reply


def test_parse_schedule_args_flow_and_station():
    args = parse_schedule_args("为东湖泵站创建流量 200 的优化任务")
    assert args["station_id"] == 1
    assert args["min_flow"] == 200
    assert args["objective_text"] == "最小化能耗"


def test_parse_schedule_args_station_number():
    args = parse_schedule_args("查看 2 号泵站机组参数")
    assert args["station_id"] == 2


def test_format_list_stations():
    text = format_tool_result("list_stations", [
        {"id": 1, "name": "东湖泵站", "location": "滨江路66号"},
    ])
    assert "东湖泵站" in text
    assert "滨江路66号" in text


def test_format_create_and_optimize():
    text = format_tool_result("create_and_optimize_schedule", {
        "task_id": 42,
        "status": "done",
        "feasible": True,
        "total_energy_kwh": 380,
        "explanation": "优化完成",
    })
    assert "任务 #42" in text
    assert "可行" in text


@pytest.mark.asyncio
async def test_try_rule_based_list_stations():
    async def mock_list(_args):
        return [{"id": 1, "name": "东湖泵站", "location": "滨江路66号"}]

    handlers = {"list_stations": mock_list}
    result = await try_rule_based_reply("列出所有泵站", handlers)
    assert result is not None
    reply, task_id = result
    assert "东湖泵站" in reply
    assert task_id is None


@pytest.mark.asyncio
async def test_try_rule_based_create_and_optimize():
    async def mock_create(args):
        return {
            "task_id": 7,
            "status": "done",
            "feasible": True,
            "total_energy_kwh": 300,
            "explanation": "ok",
        }

    handlers = {"create_and_optimize_schedule": mock_create}
    result = await try_rule_based_reply("为东湖泵站创建流量 200 的优化任务并执行", handlers)
    assert result is not None
    reply, task_id = result
    assert task_id == 7
    assert "任务 #7" in reply


@pytest.mark.asyncio
async def test_try_rule_based_no_match():
    result = await try_rule_based_reply("你好", {})
    assert result is None
