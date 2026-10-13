# Fiona 价格结构 MCP 接入与工具清单

## 目录

1. 连接与认证
2. 首次接入检查
3. 价格结构工具
4. 市场数据工具
5. 排名统计工具
6. 最小调用组合
7. 客户端模板

## 连接与认证

| MCP | URL | 作用 |
|---|---|---|
| `price_structure` | `https://track.finoview.com.cn/fiona/mcp/price_structure` | 现货、基差、期限结构、内外盘价差及主力展期 |
| `futures_market_data` | `https://track.finoview.com.cn/fiona/mcp/futures_market_data` | 交易日、品种与实际合约、行情、成交量和持仓量 |
| `futures_ranking` | `https://track.finoview.com.cn/fiona/mcp/futures_ranking` | 主力涨跌截面、历史位置和单品种季节性统计 |

三个端点的 Transport 均为 `streamable_http`。`price_structure` 需要 API Key，实际请求头为 `Authorization: Bearer <API Key>`；`futures_market_data` 和 `futures_ranking` 当前公开免鉴权，不需要 API Key，不配置 `Authorization` 请求头。真实 API Key 只能保存在客户端或平台凭证管理区，不得写入 Skill 文件、`agents/openai.yaml`、版本库、日志或对话。

优先使用客户端已注册的 MCP 工具，不自行拼接 URL 或直接发送 HTTP 请求。`agents/openai.yaml` 已声明三个依赖；支持自动安装的平台应优先使用该声明。

## 首次接入检查

“首次”是指当前客户端、账号或运行环境尚未注册这些 MCP，不在 Skill 包内保存 `is_configured` 一类状态。首次业务调用前检查当前工具列表；工具已存在时不重复安装或修改配置。

1. `price_structure` 至少应提供 `get_futures_term_structure`、`get_dominant_basis_history` 和 `get_product_roll_monitor`。
2. `futures_market_data` 至少应提供 `get_latest_futures_trading_date`、`get_futures_product_info` 和 `get_futures_timeseries_quotes`。
3. `futures_ranking` 至少应提供 `get_dominant_cross_section_change` 和 `get_symbol_overview`。
4. 工具缺失时，明确指出缺少的服务，通过平台依赖安装界面或 MCP 配置页补充上表端点。修改用户现有配置前须征得同意，只合并缺失项，不覆盖其他 MCP。
5. 只为 `price_structure` 在客户端安全凭证区配置 API Key；不要要求用户把 API Key 发到对话中。重新加载工具后，以目标品种执行当前任务所需的最小查询并确认返回正常；本次任务不需要的服务不必额外调用。

错误处理：工具不存在通常表示未安装或未重新加载；`price_structure` 的 HTTP `401`/`403` 表示 API Key 或权限问题；超时和 Transport 错误应检查 URL、网络和 `streamable_http` 支持。仅部分服务可用时，只完成其能够支持的分析并披露缺失，不能用其他服务的数据冒充。

## 价格结构工具

以下工具来自 `price_structure`，参数与字段以客户端实时 schema 为准：

- `get_futures_term_structure`：取得单品种最新及对比日期的月份合约曲线，用于 Contango、Backwardation、局部倒挂和曲线变化。
- `get_dominant_basis_history`：取得主力现货、期货和基差历史序列，用于分解基差变化。
- `get_dominant_basis_market`：取得当前主力基差率、年化口径和历史统计。
- `get_product_spot_prices`：取得品种相关现货指标；先核对地区、规格、单位、税费和日期。
- `get_cross_market_spread_market`：取得内外盘价差或价比；先核对币种、汇率、单位和合约月份。
- `get_product_roll_monitor`：取得单品种当前/目标主力及成交量、持仓量迁移证据。
- `get_roll_monitor_snapshot`：取得全市场展期快照；全市场观察时使用 `include_inactive=true`，单次 `limit` 不超过 100，并检查 `total_matched` 和 `truncated`。
- `get_product_roll_history`：取得单品种正式展期状态和成本历史。

期限结构曲线中的流动性字段可能不完整，移仓进度以 roll monitor 的成交量和持仓量为主。正式展期状态为日频 T+1 数据，不描述为盘中实时状态。

## 市场数据工具

以下工具来自 `futures_market_data`：

- `get_latest_futures_trading_date()`、`get_futures_trading_calendar(...)`：确认数据截止日和比较窗口。
- `get_futures_product_info(...)`、`get_tradable_futures_contracts(...)`、`get_futures_contract_info_table(...)`：确认品种和实际合约身份。
- `get_futures_snapshot_quotes(...)`：核对当前实际合约价格、成交量和持仓量；不用于历史时点。
- `get_futures_timeseries_quotes(...)`：取得实际合约或品种历史序列。
- `get_futures_dominant_quotes(...)`：取得主力口径序列并检查逐日 `contract` 字段中的主力切换。

长期序列按工具返回的 `columns + rows` 处理。单品种主力或单合约日线单次最多 260 个交易日，2—5 个品种或合约最多 60 个交易日，全市场日线仅限单个交易日；最终单次最多 500 行。跨一年或三年窗口时分段取数、按交易日去重拼接，并检查主力切换和复权口径。

## 排名统计工具

以下工具来自 `futures_ranking`：

- `get_dominant_cross_section_change(symbol, date, periods, percentile_years, limit)`：取得全市场或指定品种的主力涨跌截面；需要价格水平分位时传 `percentile_years=1,3`。
- `get_symbol_overview(symbol, date, history_years, sections)`：取得单品种多周期表现、季节性及相关指标分位。

板块资金统计和其他指标排名不是本 Skill 的默认调用。截面结果必须检查 `total`、`returned` 和 `truncated`；基期缺失、派生指标异常或流动性证据不足的条目不参加排名。价格水平分位不得与日涨跌幅、基差率或波动率分位混写。

## 最小调用组合

| 问题 | 首选调用 | 按需补充 |
|---|---|---|
| 单品种期限结构 | term structure | actual-contract snapshot、对比日期曲线 |
| 基差与现货强弱 | dominant basis history + basis market | spot prices |
| 主力迁移进度 | product roll monitor | actual-contract quotes、roll history |
| 全市场展期状态 | roll monitor snapshot | dominant cross-section change |
| 主力涨跌与历史位置 | dominant cross-section change | symbol overview |
| 单品种季节性 | symbol overview | dominant quotes 验证换月影响 |
| 地区现货价差 | spot prices | 本地单位转换与共同日期对齐 |
| 内外盘结构 | cross-market spread market | 汇率、合约月份和交易时段核对 |

## 客户端模板

不支持 `agents/openai.yaml` 自动安装时，按客户端选取对应模板，将其中的 server 配置合并到用户现有配置：

- Claude：`../templates/claude/mcp.json`
- OpenCode：`../templates/opencode/mcp.json`
- OpenClaw：`../templates/openclaw/mcp.json`
- WorkBuddy：`../templates/workbuddy/mcp.json`

模板中只有 `price_structure` 使用 `<your-authorized-mcp-token>` 占位符；只能在本地安全配置中替换，不能提交包含真实 API Key 的模板。
