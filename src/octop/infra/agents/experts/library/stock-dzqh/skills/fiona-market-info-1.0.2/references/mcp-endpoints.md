# 市场基础信息 MCP 能力清单

统一端点前缀：`https://track.finoview.com.cn/fiona/mcp/`；传输方式以当前 MCP 客户端配置为准。`futures_market_data`、`futures_ranking` 和 `market_calculate` 当前公开免鉴权，不需要 API Key，不配置 `Authorization` 请求头。

## `futures_market_data`

| 问题 | 工具 |
| --- | --- |
| 交易日历、最近/下一交易日 | `get_futures_trading_calendar`、`get_latest_futures_trading_date`、`get_next_futures_trading_date` |
| 品种、合约和交易参数 | `get_futures_product_info`、`get_tradable_futures_contracts`、`get_futures_contract_info_table`、`get_futures_contract_trading_params` |
| 快照与历史行情 | `get_futures_snapshot_quotes`、`get_futures_timeseries_quotes`、`get_futures_dominant_quotes` |
| 会员、波动率与仓单 | `get_futures_member_company_names`、`get_futures_member_positions`、`get_futures_volatility`、`get_futures_warehouse_quantity`、`get_futures_warehouse_distribution` |

## `futures_ranking`

- `get_section_statistics`：板块/品种时间区间统计。
- `get_ranking_indicators`：各品种可用排名指标枚举。
- `get_product_ranking`：按指标、日期、品种和排序方向进行排名。
- `get_dominant_cross_section_change`：主力合约横截面涨跌幅变化对比。
- `get_symbol_overview`：品种概览与相关统计（季节性、历史分位数）。

## `market_calculate`

- `get_type_positions_amount`：合约/品种成交量、成交额、持仓量、持仓额（全市场持仓背景）
- `get_product_fund_flow`、`get_product_speculation`：品种沉淀资金、资金流向与投机度。
