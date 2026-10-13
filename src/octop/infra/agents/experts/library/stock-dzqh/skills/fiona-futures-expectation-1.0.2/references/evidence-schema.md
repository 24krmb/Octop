# 预期研判证据结构

调用 MCP 后，先将结果整理成中间结构，再生成情景判断。原始事实与模型推断必须分开。

```json
{
  "instrument": {"symbol": "", "contract": "", "exchange": "", "market": ""},
  "as_of": "",
  "query_window": {"start": "", "end": "", "frequency": ""},
  "facts": [],
  "market_structure": [],
  "expectations": [],
  "viewpoints": [],
  "inferences": [],
  "uncertainties": [],
  "scenarios": []
}
```

- `facts`：品种、合约、交易日、行情、持仓、仓单等可核验事实。
- `market_structure`：时间序列、截面排名、主力合约变化和成交持仓统计。
- `expectations`：`rating_prediction` 返回的市场预期分布或东证观点序列；保留报告类型和实际数据日期。
- `viewpoints`：`viewpoint` 返回的研报、周度观点、研究员观点或动态快评；保留原文标识和发布时间。
- `inferences`：基于证据形成的传导关系或判断，必须注明证据强度。
- `uncertainties`：数据缺失、滞后、截断、冲突和未核实事项。
- `scenarios`：基准、偏强、偏弱情景及其触发条件、验证指标和失效条件。

证据记录至少包含：来源 MCP、工具名、查询参数、实际数据日期、样本范围、单位、返回数量及是否截断。机构观点分布不得写成价格概率；证据不足时不得补造概率、目标价或交易信号。
