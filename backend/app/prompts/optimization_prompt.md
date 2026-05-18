# 能效优化调度 Prompt

你现在需要根据以下泵站信息制定最优调度方案。

## 泵站与机组信息
{station_info}

## 当前工况数据
{operating_data}

## 调度目标
{objective}

## 约束条件
{constraints}

## 输出要求
请以JSON格式输出调度方案，包含以下字段：
```json
{
  "plan": [
    {
      "unit_id": 1,
      "unit_name": "1号机组",
      "action": "启动/停止/维持",
      "target_power_kw": 150.0,
      "target_flow": 80.0
    }
  ],
  "total_energy_kwh": 1200.5,
  "total_flow": 240.0,
  "explanation": "方案说明..."
}
```

请确保：
1. 满足所有约束条件
2. 在约束允许范围内使能耗最小化
3. 给出清晰的方案说明与决策依据
