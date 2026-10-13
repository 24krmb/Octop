# Fiona 会员席位持仓 MCP 工具清单

## 连接

- `futures_market_data`: `https://track.finoview.com.cn/fiona/mcp/futures_market_data`
- `market_data_calculate`: `https://track.finoview.com.cn/fiona/mcp/market_calculate`
- Transport: `streamable_http`
- Authentication: 两个端点当前公开免鉴权，不需要 API Key，不要配置 `Authorization` 请求头。

从数据工具取得原始席位数据后，按照 [会员持仓分析规范](analysis-methods.md) 自行写代码计算排名、集中度、多空比、净持仓和增减。

两个 MCP 都直接返回后端字段，字段名以中文为主（如 `交易日期`、`品种代码`、`合约代码`、`会员简称`、`持仓类型`）。首次调用应先观察实际返回的字段名与取值，不要只凭本文档假设英文 key。

## 期货市场基础数据工具（futures_market_data）

| 工具 | 用途 | 关键参数或限制 |
|---|---|---|
| `get_futures_member_positions` | **主接口**：合约×会员×持仓类型的成交量/多头/空头持仓及增减（单位：手） | `start_date`/`end_date`、`symbol`（单品种）、`contract`、`member_name`、`position_type`；默认 `limit=200`，最大 500 |
| `get_futures_member_company_names` | 获取标准会员简称列表，校验席位名称 | 无参数 |
| `get_latest_futures_trading_date` | 最近一个已完成交易日 | 无参数 |
| `get_futures_trading_calendar` | 对齐交易日与窗口参考日 | `start_date`, `end_date` |
| `get_tradable_futures_contracts` | 指定交易日可交易合约列表 | `date`, `symbol`（1 至 3 个品种） |
| `get_futures_product_info` | 识别品种、交易所和板块 | `symbol?`, `exchange?`, `section?` |
| `get_futures_dominant_quotes` | 主力价格、成交量、持仓量时序（结构背景，可能含结算价/昨结算价） | `start_date`, `end_date`, `symbol?`, `frequency`；日线最多 5 个品种 |
| `get_futures_timeseries_quotes` | 指定合约历史行情（OHLC、成交量、持仓量，可能含结算价） | `start_date`, `end_date`, `symbol?`, `contract?`, `frequency`；日线最多 60 个交易日 |
| `get_futures_snapshot_quotes` | 最新快照行情（最新价、OHLC、成交量、持仓量） | `symbol?`, `contract?` |
| `get_futures_contract_trading_params` | 合约交易参数（合约乘数、最小变动价位、保证金、手续费、涨跌停） | `contract` 必填, `date?` |
| `get_futures_contract_info_table` | 合约静态信息（上市日、最后交易日、状态） | `contract` |

行情接口返回字段以实际为准，通常包含 `结算价`、`昨结算价`（或英文等价）；若某次返回没有结算价，用 `收盘价` 近似并在结论中说明。合约乘数统一从 `get_futures_contract_trading_params` 获取。

### `get_futures_member_positions` 口径

- 返回结构：`items`（每项含 `交易日期`、`品种代码`、`合约代码`、`会员简称`、`持仓类型`、`成交/持仓量(手)`、`成交/持仓量变化(手)`）、`total`、`returned`、`truncated`、`hint`。
- `position_type` 取值：`1`/`trade_volume`/`volume`/`成交量` 表示成交量；`2`/`long_position`/`long`/`多头持仓` 表示多头持仓；`3`/`short_position`/`short`/`空头持仓` 表示空头持仓。留空一次返回三种类型，多值逗号分隔。
- 默认 `limit=200` 可覆盖前 20 席位，但必须核对 `truncated`；被截断时缩小过滤条件再查。
- “变化”字段是较上一交易日的增减，使用前用相邻交易日原始值复核。

## 成交持仓与金额计算工具（market_data_calculate）

| 工具 | 用途 | 关键参数或限制 |
|---|---|---|
| `get_member_position_summary` | 品种×会员的多/空/净持仓汇总（量与额） | `start_date`, `end_date`, `symbol`, `member_name`；默认 `limit=200` |
| `get_member_position_amounts` | 合约×会员成交/持仓额明细（金额口径） | `start_date`/`end_date`, `symbol`, `contract`, `member_name`, `position_type`；默认 `limit=200` |
| `get_company_contract_opening_process` | 单会员×单合约逐日建仓过程（多/空/净持仓、持仓均价、当日盈亏） | `member_name`、`contract` 必填；`start_date`, `end_date` |
| `get_company_type_profit` | 公司×品种区间累计盈亏分布 | `dimension`（by_symbol/by_company）、`symbol` 或 `member_name` |
| `get_company_type_profit_series` | 公司×品种每日盈亏序列 | `symbol`、`member_name` 必填 |
| `get_type_positions_amount` | 合约/品种成交量、成交额、持仓量、持仓额（全市场持仓背景） | `start_date`, `end_date`, `symbol?`, `contract?` |
| `get_product_speculation` | 品种投机度（背景） | `start_date`, `end_date`, `symbol?` |

### 关键口径差异

- `get_futures_member_positions` 是“手”，`get_member_position_amounts` 是“元”（成交额/持仓额 = 数量 × 结算价 × 合约乘数）。金额口径适合横向比较不同品种的资金权重，但排名和集中度优先用手数。
- `get_member_position_summary` 是品种级汇总（跨合约合并），其“净持仓”是品种口径；单合约净持仓用 `get_futures_member_positions` 的多空相减。
- `get_company_contract_opening_process` 的“持仓均价”和“当日盈亏”由服务端计算，仅描述该会员该合约，不代表市场整体。

## 典型调用顺序

### 单合约席位分析

1. 调用 `get_latest_futures_trading_date` 或 `get_futures_trading_calendar` 确认截止日。
2. 调用 `get_futures_member_positions`，传 `contract` 与 `position_type=2,3`，`limit=500` 并核对 `truncated`。
3. 需要成交量排名时再传 `position_type=1`；需要增减对比时用“变化”字段或查相邻交易日。
4. 本地计算排名、集中度、多空比、净持仓和增减；必要时运行 `scripts/analyze_positions.py analyze`。

### 单品种会员汇总

1. 调用 `get_member_position_summary`（传 `symbol`）获得品种级多/空/净持仓。
2. 需要单会员跨品种方向时传 `member_name`；需要多会员合并方向时传多个会员。
3. 需要金额口径或席位盈亏时调用 `get_member_position_amounts`、`get_company_type_profit`。

### 重点席位跟踪

1. 用 `get_futures_member_company_names` 确认标准简称。
2. 调用 `get_company_contract_opening_process`（`member_name` + `contract`）看逐日建仓节奏。
3. 结合 `get_company_type_profit_series` 看该席位在该品种的每日盈亏。

### 板块或全市场截面

1. 用 `get_futures_product_info` 确定品种范围。
2. 逐品种调用 `get_member_position_summary`，按同一截止日合并后比较净持仓与方向。
3. 全市场席位明细不可一次拉取（数据量极大），必须按品种/合约分批，并逐一核对 `truncated`。

## 时间与口径

- `start_date`/`end_date` 均留空返回数据库中最新可用交易日；席位数据盘后发布，约 17:00 后接口会更新当日新数据。始终报告实际命中的交易日。
- 所有历史工具按截止日或此前最近有效交易日解析；报告时写出实际交易日，不写用户给的近似日期。
- 排名、集中度、多空比只对同一交易日、同一合约、同一持仓类型计算。
- 会员持仓只覆盖交易所公布的席位（通常前 20 名），与品种总持仓不同；需要总持仓时用 `get_type_positions_amount` 或行情接口的持仓量并说明口径。
