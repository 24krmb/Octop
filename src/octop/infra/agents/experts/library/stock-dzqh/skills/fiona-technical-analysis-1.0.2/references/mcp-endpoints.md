# Fiona 技术面分析 MCP 工具清单

## 目录

1. 连接
2. 技术分析工具
3. 盘中监控工具
4. 市场数据工具
5. 最小调用组合

## 连接

| MCP | URL | 作用 |
|---|---|---|
| `fiona-technical-analysis` | `https://track.finoview.com.cn/fiona/mcp/technical-analysis` | 预计算多周期 TA 最新截面与时间序列 |
| `fiona-intraday-monitor` | `https://track.finoview.com.cn/fiona/mcp/intraday-monitor` | 盘中市场扫描、实际合约下钻和相关资讯 |
| `futures_market_data` | `https://track.finoview.com.cn/fiona/mcp/futures_market_data` | 交易日、合约、快照、OHLCV及波动率 |

Transport 均为 `streamable_http`。`technical-analysis` 和 `intraday-monitor` 需要 API Key，实际以 `Authorization: Bearer <API Key>` 鉴权；`futures_market_data` 当前公开免鉴权，不需要 API Key。不得在 Skill 或仓库中保存真实凭证。优先调用已注册工具，不自行构造 HTTP 请求。

## 技术分析工具

### `futures_ta_cross_section`

查询一个或多个 `888` 连续合约在多个频率下的最新 TA 结果。

| 参数 | 说明 |
|---|---|
| `contracts` | 如 `RB888`, `CU888`；空列表查询有缓存覆盖的全部连续合约，最多100个 |
| `frequencies` | `1m`, `5m`, `15m`, `30m`, `60m`, `1d`；空值返回全部 |

核心返回包括合约、频率、是否可用、最新时间、综合信号、多空中性投票，以及 SMA、动量、叠加、枢轴和K线形态分类明细。日频返回六类预计算信号。

用于：最新多周期状态、技术面横向筛选和信号来源解释。

限制：这是最新截面，不能证明信号何时变化或持续多久；连续合约不是实际可交易合约。

### `futures_contract_ta_series`

查询一个连续合约逐根K线对齐的多频率 TA 序列。

| 参数 | 说明 |
|---|---|
| `contract` | 单个连续合约，如 `RB888` |
| `frequencies` | 支持 `1m`, `5m`, `15m`, `30m`, `60m`, `1d` |
| `start_time`, `end_time` | 可选 ISO 8601 时间；起始不得晚于结束 |
| `limit` | 每个频率1—2000行，默认200 |

每行包括时间、五类信号、综合信号及多空中性票数。

用于：判断信号切换时间、连续长度、扩散顺序和近期反复。

## 盘中监控工具

### `intraday_market_scan`

扫描国内期货主力合约的盘中状态。

| 参数 | 说明 |
|---|---|
| `sections` | 板块筛选；空值为全市场 |
| `product_types` | 服务端支持的品种类别 |
| `symbols` | 品种代码列表，如 `RB`, `I`, `CU` |
| `lookback_minutes` | 30、60或120个有效交易分钟 |
| `start_time`, `end_time` | 自定义区间，必须同时提供 |
| `top_n` | 各榜单1—20条 |

返回市场广度、板块强弱、领涨领跌、成交活跃度、持仓变化、沉淀资金估算、异常、候选下钻品种、实际主力合约和数据质量。

用于：发现候选品种和验证技术截面是否得到价格、成交与持仓支持。不要把沉淀资金绝对额直接解释为方向偏好。

### `intraday_contract_analysis`

下钻一个品种或实际合约的当前盘中状态。

| 参数 | 说明 |
|---|---|
| `symbol_or_contract` | 品种或实际合约，如 `RB`、`RB2610` |
| `frequency` | `5m`, `15m`, `30m`, `60m` |
| `window` | `30m`, `60m`, `120m`, `morning`, `afternoon`, `custom` |
| `start_time`, `end_time` | `custom` 时必须同时提供 |

返回实际主力、连续技术序列标识、最新快照、窗口涨跌、成交活跃度、持仓与资金变化、MA5/10/20/60、MACD、RSI14、ATR14、20周期高低点、缺口、关键位置、突破确认、趋势切换、分钟K和数据质量。

用于：当前状态、实际合约关键位、量价持仓确认和反弹/反转判断。

注意：`change_pct` 是当日相对前结算/前收的涨跌；`window_price_change_pct` 是所选窗口涨跌。

字段来源必须分开：

| 字段 | 来源与用途 |
|---|---|
| `latest_snapshot`, `window_metrics`, `intraday_technical`, `minute_bars` | 实际主力合约，可用于当前价格与盘中关键位 |
| `price_structure.day_open/day_high/day_low/gap_*` | 实际主力快照和分钟数据，可用于实际合约缺口与日内结构 |
| `daily_technical`, `daily_bars` | `technical_series_contract` 的连续日线，只作方向背景 |
| `key_levels.window_high/window_low/day_open` | 实际合约盘中窗口 |
| `key_levels.previous_day_high/low`, `daily_high/low_20_previous` | 连续日线，不得直接列为实际合约支撑压力 |

`trend_transition` 会同时参考实际盘中和连续日线背景。可使用其分类描述状态，但涉及具体价位时必须回到上述字段来源；需要实际合约日线高低点时另调市场数据时序。

`breakout_confirmation`、`trend_transition`、窗口成交活跃度和持仓确认均按调用时的当前窗口计算。它们不能回答过去某一时点当时会返回什么；历史复盘应改用截止时点的实际合约K线和 TA series。若 `custom` 历史下钻失败，不要退而把当前下钻结果当历史结果。

### `intraday_related_news`

查询与盘中分析相关的已标记资讯。

| 参数 | 说明 |
|---|---|
| `start_time`, `end_time` | `YYYY-MM-DD HH:MM:SS`，跨度不超过24小时 |
| `product_codes` | 品种代码列表 |
| `important` | 是否仅看重要资讯 |

仅用于验证事件关联。空结果写“当前未发现可验证的相关资讯”，不等于没有影响，也不得补造催化。返回资讯时核对发布时间是否早于价格变化、产品映射和内容机制；工具命中只能支持时间相关或可能关联，不能独立证明因果。

## 市场数据工具

### 交易日与品种识别

- `get_latest_futures_trading_date()`：确认最近有效交易日。
- `get_futures_trading_calendar(start_date, end_date, limit)`：对齐交易窗口。
- `get_futures_product_info(symbol?, exchange?, section?, limit)`：确认品种代码、名称、交易所和板块。
- `get_tradable_futures_contracts(date, symbol, limit)`：确认指定交易日可交易合约。
- `get_futures_contract_info_table(contract, limit)`：核对实际合约信息。

### 行情

- `get_futures_snapshot_quotes(symbol?, contract?, limit)`：获取当前快照；不支持历史日期。
- `get_futures_timeseries_quotes(start_date, end_date, symbol?, contract?, frequency, limit)`：获取实际合约或品种时序。支持 `1d`, `1m`, `5m`, `15m`, `30m`, `60m`；分钟频率必须限定合约，日期跨度受频率限制。
- `get_futures_dominant_quotes(start_date, end_date, symbol?, frequency, limit)`：获取主力口径 OHLCV；单次最多5个品种，返回行数默认200、最大500，检查截断和主力切换。

历史序列用于验证趋势、计算价格结构和补足盘中 MCP 未覆盖的区间。必须保留实际日期、合约、OHLCV字段和截断标记。

冻结时点分析时，先验证K线标签语义并仅纳入截止时点已经完成的记录；为MA、MACD、RSI、ATR等自算指标请求足够的预热区间。报告计算公式和初始化差异，尤其不要把简单均值ATR与Wilder ATR混称为同一数值。

夜盘切片必须同时检查分钟记录的时间戳和交易日归属。分别计算上一日盘收盘到夜盘开盘、夜盘内部、夜盘收盘到当日日盘开盘；交易所休市段不是缺失K线，不按连续自然分钟补齐。

换月分析优先从 `get_futures_dominant_quotes` 检查逐日 `contract` 是否变化，再用 `get_futures_snapshot_quotes` 和两个实际合约时序核验价差、成交与持仓迁移。若返回没有连续序列复权标志或切换规则，不得断言 `888` 使用前复权、后复权或不复权，也不得把候选合约价差直接当成已经发生的连续图跳空。

### 波动率

`get_futures_volatility(start_date, end_date, symbol?, volatility_type, limit)`：

- `historical`：20/40/60/120日历史波动率；
- `implied`：主力相关期权平值及1/2/3月隐含波动率；
- `all`：按交易日、品种和主力合约合并两类指标。

所有波动率指标单位为百分比。隐含波动率可能因品种无活跃期权或数据缺失而为空；不得用历史波动率代填。

调用后检查 `returned`、`truncated` 及 `items` 的实际首末交易日。即使请求截止今天，返回序列也可能停在更早日期；不得把过期末值描述为当前波动率。判断扩张或收缩必须比较同一指标的时间序列，不能比较不同K线周期的单点ATR。

跨品种比较只对齐相同交易日和相同字段，例如两品种的 `historical_volatility_20` 或相同隐含期限；不要把某品种ATM IV与另一品种HV20直接排名。若返回主力合约不同于当前实际主力，额外披露合约错位。

兼容旧部署时，若工具列表没有 `get_futures_volatility`，分别使用 `get_futures_historical_volatility` 和 `get_futures_implied_volatility`，按交易日、品种和主力合约对齐后再分析；不要因合并工具不存在而猜造返回。

## 最小调用组合

| 问题 | 首选 | 按需补充 |
|---|---|---|
| 当前单品种技术面 | `intraday_contract_analysis` | TA cross-section、volatility |
| 多周期是否一致 | TA cross-section | contract analysis验证实际行情 |
| 刚转强还是持续 | TA series | cross-section确认最新状态 |
| 全市场技术筛选 | TA cross-section | market scan筛少量候选 |
| 历史区间技术分析 | trading date + quotes | TA series、volatility、本地脚本 |
| 突破是否有效 | contract analysis | raw OHLCV、TA series |
| 异动原因 | 先完成技术分析 | related news |
| 夜盘与日盘拆分 | actual-contract minute quotes | TA series、contract analysis |
| 连续图疑似换月跳变 | dominant quotes + old/new actual contracts | cross-section、contract analysis |
| 截止历史时点的判断 | actual-contract quotes + TA series with end_time | 当前下钻只作事后对照 |
| 历史突破或假突破复盘 | actual-contract minute quotes | TA series重建信号演变 |
| 跨品种趋势与波动比较 | same-window contract analysis + aligned volatility | cross-section |
| 盘中波动压缩 | actual-contract minute quotes | contract analysis、TA series、volatility背景 |
