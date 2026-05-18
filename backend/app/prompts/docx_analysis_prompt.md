# 政府文书分析 Prompt

你需要分析以下政府水利调度文书的内容。

## 文书内容
{document_content}

## 分析模式：{mode}

### 模式一：问答分析（mode=qa）
请根据文书内容回答用户的问题。如果文书中没有相关信息，请如实说明。

用户问题：{question}

### 模式二：参数提取（mode=extract）
请从文书中提取调度相关的关键参数，以JSON格式输出：
```json
{
  "objective": "调度目标描述",
  "constraints": {
    "min_flow": null,
    "max_flow": null,
    "min_head": null,
    "max_head": null,
    "max_units_running": null,
    "time_periods": [],
    "other": []
  },
  "target_stations": ["涉及的泵站名称"],
  "deadline": "要求完成时间",
  "priority": "紧急程度",
  "raw_requirements": ["原文中的具体要求条目"]
}
```

请尽可能从文书中提取完整信息，未提及的字段填null。
