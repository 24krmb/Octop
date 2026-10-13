# 市场预期研判 MCP 能力清单

端点前缀：`https://track.finoview.com.cn/fiona/mcp/`。`rating_prediction` 需要 API Key，实际以 `Authorization: Bearer <API Key>` 鉴权；`futures_market_data`、`futures_ranking` 和 `viewpoint` 当前公开免鉴权，不需要 API Key。真实 API Key 只能保存在 MCP 客户端的安全凭证区。

## `futures_market_data`

用于标准化品种/合约、确认交易日，以及获取快照、历史/主力行情、会员持仓、波动率和仓单等事实数据。常用工具：`get_futures_product_info`、`get_latest_futures_trading_date`、`get_futures_snapshot_quotes`、`get_futures_timeseries_quotes`、`get_futures_dominant_quotes`、`get_futures_member_positions`、`get_futures_volatility`。

## `rating_prediction`（主要 MCP）

- `get_market_expectation_cross_section`：指定报告日的市场预期分布。
- `get_market_expectation_timeseries`：daily/weekly 市场预期变化。
- `get_dongzheng_viewpoint_cross_section`：指定报告日的东证自有观点截面。
- `get_dongzheng_viewpoint_timeseries`：东证自有观点时间序列。

注意 `report_type` 只能使用接口支持的 `daily` 或 `weekly`；记录实际返回日期、样本数量和截断状态。

## `viewpoint`（辅助 MCP）

仅在客户明确询问 DZ 观点库、周度观点或动态快评，或需要对 `rating_prediction` 的市场预期进行辅助交叉验证时使用。用于检索观点库、研究员观点、周度/周期观点和动态快评。常用能力包括观点检索、周度观点查询、动态检索和动态详情查询。不得把 `viewpoint` 结果当作市场整体预期。

当前 `/mcp/viewpoint` 不包含独立研报搜索、研报详情或 PDF 下载能力；这些能力如需使用，应单独接入 `report` MCP，不能在本 skill 中假设存在。

观点文本不应直接当作事实或价格预测，必须保留观点对象、发布时间、来源和观点标识。

## `futures_ranking`

使用 `get_section_statistics`、`get_ranking_indicators`、`get_product_ranking`、`get_dominant_cross_section_change` 和 `get_symbol_overview`，验证品种相对表现、横截面变化与统计稳定性。

注意：`futures_ranking` 提供的是市场统计和相对比较，不等于供需基本面结论，也不等于价格预测。

所有统计结果都要保留查询区间、排序方向、单位、样本数和 `truncated` 状态。
