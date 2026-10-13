# Optional MCP 指南（可选 MCP）

本文件说明 `fiona-foreign-data` Skill 可选使用的 MCP 接口、主要作用和使用要点。此文件为可选增强，Skill 在未启用这些 MCP 时仍能工作。

## 概览

该 Skill 的基础能力由foreign MCP 的两项核心工具支持：`get_foreign_domestic_mapping`（内外盘映射）和 `get_foreign_market_analysis`（外盘区间行情分析）。在需要更深入的跨市场比对、盘前参考、跳空推断或风险度量时，可以额外调用以下 MCP：

盘前预警的完整取数顺序和时间窗口见 [盘前预警取数规则](pre-market-warning.md)。其中 `/mcp/futures_market_data` 是日常盘前对照获取国内行情的必需数据源，不应使用长图代码中的米筐接口替代。

- `/mcp/futures_market_data` — 期货市场基础数据（用于获取内盘对应品种的历史价格、截面行情、交易日历等）
- `/mcp/news` — 早间新闻资讯（用于核对行情变动时是否存在时间上匹配的新闻事件）
- `/mcp/economic_calendar` — 宏观经济事件与市场假期（用于识别可能影响行情的宏观事件或交易日变更）

## `/mcp/futures_market_data` 重点端点

- `get_futures_trading_calendar`
- `get_latest_futures_trading_date`
- `get_next_futures_trading_date`
- `get_futures_product_info`
- `get_tradable_futures_contracts`
- `get_futures_contract_info_table`
- `get_futures_contract_trading_params`
- `get_futures_snapshot_quotes`
- `get_futures_timeseries_quotes`
- `get_futures_dominant_quotes`
- `get_futures_member_company_names`
- `get_futures_member_positions`
- `get_futures_historical_volatility`
- `get_futures_implied_volatility`
- `get_futures_warehouse_quantity`
- `get_futures_warehouse_distribution`

使用要点：
- 当需要把外盘走势与国内主力或标的做对比时，优先用 `get_futures_timeseries_quotes`（或 `get_futures_dominant_quotes`）按同样的时间区间拉取内盘历史价格序列。
- 注意价格字段的口径匹配：外盘返回的价格可能包含 `earliest_price`（最早价）、`latest_price` / `last_price`（最新或最后价）、`high_price`（最高价）、`low_price`（最低价）等；在对齐时要选择一致的口径，例如用“分钟级收盘价”对比外盘的同口径分钟收盘价。
- 分钟序列通常使用该 MCP 的分钟级 `close` 值作为收盘价对齐点；如果外盘 `include_series` 返回的是以“最早价格/最后价格”命名的字段，先确认字段含义再映射。

假期／区间报告默认公开检索资讯；以下资讯工具仅在已接入且本次需要时使用，不将其缺失当作无法生成报告。

## `/mcp/news`（新闻） 重点端点

- `get_mornings_news_data`
- `get_fino_news_ai_tagged`
- `get_fino_ai_collection`

使用要点：
- 仅用于发现可能时间上匹配的新闻事件或标签，不在 Skill 内自动判定新闻与价格变动的因果关系。
- 当行情出现显著跳空或异常波动时，检索事件时间窗内的新闻并在输出中列出候选事件与来源。

## `/mcp/economic_calendar` 重点端点

- `get_economic_indicators`
- `get_economic_events`
- `get_market_holidays`
- `get_economic_indicator_detail`

使用要点：
- 用于识别宏观日程（例如重要数据发布时间）、市场假期或交易日变更，这些因素可解释或排除某些跳空和成交异常。

## 连接

- `futures_market_data`:`https://track.finoview.com.cn/fiona/mcp/futures_market_data`
- `news`:`https://track.finoview.com.cn/fiona/mcp/news`
- `economic_calendar`:`https://track.finoview.com.cn/fiona/mcp/economic_calendar`
- `foreign`:`https://track.finoview.com.cn/fiona/mcp/foreign`

鉴权说明：`foreign`、`news` 和 `economic_calendar` 需要 API Key，实际以 `Authorization: Bearer <API Key>` 鉴权；`futures_market_data` 当前公开免鉴权，不需要 API Key。只为实际使用的需鉴权端点配置凭证，不在 Skill 或仓库中写入真实 API Key。

