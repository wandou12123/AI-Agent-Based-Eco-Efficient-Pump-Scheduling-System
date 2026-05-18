# 安全校验 Prompt

请对以下调度方案进行安全校验。

## 调度方案
{plan}

## 安全约束阈值
{safety_thresholds}

## 当前工况
{operating_data}

## 校验要求
请逐项检查以下安全条件：
1. 各机组运行功率是否在额定范围内
2. 总流量是否满足最低/最高要求
3. 水位是否在安全范围内
4. 同时运行台数是否超限
5. 电流是否超过额定值
6. 机组启停次数是否过于频繁

## 输出格式
```json
{
  "passed": true/false,
  "checks": [
    {"item": "功率范围", "passed": true, "detail": "所有机组功率在额定范围内"},
    {"item": "流量要求", "passed": true, "detail": "总流量240m³/h，满足最低要求200m³/h"}
  ],
  "warnings": ["可选的警告信息"],
  "suggestion": "如不通过，给出修改建议"
}
```
