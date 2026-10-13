# Fiona 仓单库存与交割压力 MCP 接入与工具清单

## 目录

1. 连接与认证
2. 首次接入检查
3. 期货市场数据工具
4. 产业库存工具
5. 最小调用组合

## 连接与认证

| MCP | URL | 作用 |
|---|---|---|
| `futures_market_data` | `https://track.finoview.com.cn/fiona/mcp/futures_market_data` | 交易日、品种与合约、行情与持仓、注册仓单、仓库分布及会员持仓 |
| `dzlabel` | `https://track.finoview.com.cn/fiona/mcp/dzlabel` | 社会库存、工厂库存、港口库存等产业指标的发现与时序查询 |

两个端点的 Transport 均为 `streamable_http`。`dzlabel` 需要 API Key，实际请求头为 `Authorization: Bearer <API Key>`；`futures_market_data` 当前公开免鉴权，不需要 API Key，不配置 `Authorization` 请求头。真实 API Key 只能保存在客户端或平台的凭证管理区，不得写入 `SKILL.md`、本参考文件、`agents/openai.yaml`、版本库或对话正文。

优先调用客户端已经注册的 MCP 工具，不自行拼接 URL、请求头或直接发送 HTTP 请求。Skill 包中的 `agents/openai.yaml` 已声明这两个依赖；支持依赖自动安装的平台应优先使用该声明完成接入。

## 首次接入检查

“首次”是指当前客户端、账号或运行环境尚未注册这些 MCP，而不是在 Skill 包内维护 `is_signed` 一类状态。每次准备调用业务数据前，先检查当前工具列表；已经可用时不要重复安装或修改配置。

1. 检查 `futures_market_data` 下是否至少存在 `get_latest_futures_trading_date`、`get_futures_product_info` 和 `get_futures_warehouse_quantity`。
2. 检查 `dzlabel` 下是否至少存在 `get_products`、`search_indicators` 和 `get_indicator_series`。
3. 若工具缺失，明确告诉用户缺少哪个 MCP，并引导用户通过平台的依赖安装界面或 MCP 配置页添加上表端点。修改现有 MCP 配置前应征得用户同意，只补充缺失项，不覆盖其他服务。
4. 只为 `dzlabel` 在客户端的安全凭证区配置服务方提供的 API Key。不要要求用户把 API Key 粘贴到对话中，也不要把 API Key 落入 Skill 目录。
5. 安装或修改配置后，按客户端要求重新加载 MCP 工具；先调用 `get_latest_futures_trading_date()` 和 `get_products()` 做最小健康检查，通过后再执行正式分析。

常见失败应这样区分：

- 工具列表中没有工具：依赖尚未安装，或安装后尚未重新加载。
- `dzlabel` 返回 HTTP `401` 或 `403`：API Key 缺失、失效或无权访问。
- 连接超时或 Transport 错误：检查 URL、网络和客户端是否支持 `streamable_http`。
- 仅一个端点健康：只使用已验证的数据源，并在输出中披露缺失；不得假装另一个端点的数据已经取得。

## 期货市场数据工具

以下工具来自 `futures_market_data`。调用时以客户端展示的实时工具 schema 为准，不猜造未公开参数。

### 交易日、品种与合约

- `get_latest_futures_trading_date()`：确认最近有效交易日。
- `get_futures_trading_calendar(start_date, end_date, limit)`：对齐观察日和剩余交易日。
- `get_futures_product_info(symbol?, exchange?, section?, limit)`：确认品种代码、名称、交易所和板块。
- `get_tradable_futures_contracts(date, symbol, limit)`：取得指定交易日可交易的实际合约。
- `get_futures_contract_info_table(contract, limit)`：查询具体合约资料和最后交易日等字段。
- `get_futures_contract_trading_params(contract, date?)`：核对合约乘数、交易单位等可用交易参数。

合约资料不能替代完整交割规则。交割单位、交割品级、品牌、地点、仓单有效期和交割流程仍应以交易所当期规则为准。

### 行情与持仓

- `get_futures_snapshot_quotes(symbol?, contract?, limit)`：查询当前具体合约快照和持仓量；不用于历史时点。
- `get_futures_timeseries_quotes(start_date, end_date, symbol?, contract?, frequency, limit)`：查询具体合约行情与持仓时序；交割压力分析通常使用实际合约和 `1d` 频率。
- `get_futures_member_positions(start_date, end_date, symbol, contract, member_name, position_type, limit)`：按需查询会员持仓，用于集中度交叉验证；单次返回上限以工具 schema 为准。

目标临月合约持仓必须来自具体合约行情或持仓工具，不能用仓单接口附带的品种总持仓、主力持仓或连续合约替代。

### 仓单与仓库

- `get_futures_warehouse_quantity`：查询注册仓单数量、变化及服务端提供的折合手数。调用前读取实际 schema，按品种和日期范围传参。
- `get_futures_warehouse_distribution`：查询指定交割仓库目录或仓单地区分布。若返回结果只有仓库名称和地址、没有数量，不计算地区集中度。

仓单时序单次查询最多 60 个自然日、最多 3 个品种、最多 500 行；更长区间应分段请求、按日期去重拼接，并检查返回中的行数和截断标记。仓单接口附带的持仓字段若为品种口径，只能作背景，不能用于计算目标合约仓单覆盖率。

## 产业库存工具

以下工具来自 `dzlabel`：

- `get_products()`：取得品种树并确认目标品种的 `product_id`。
- `search_indicators(product_id, keyword, limit)`：按“社会库存”“工厂库存”“港口库存”“产成品库存”等关键词搜索指标。
- `expand_catalog(node_id, return_indicator_count)`：需要浏览指标目录时展开节点。
- `get_indicators(node_id, limit)`：列出节点下的指标；单次上限以工具 schema 为准。
- `get_indicator_series(indicator_ids, start_date, end_date)`：查询选定指标的时间序列，日期格式使用 `YYYYMMDD`。

推荐调用链为：`get_products` → `search_indicators` → 必要时 `expand_catalog` / `get_indicators` → `get_indicator_series`。每次只选择与目标品种最相关的少数指标，并核对单位、频率、统计范围、更新时间和是否修订。产业库存是潜在补货背景，不等同于注册仓单；来源不能证明互不重叠时不得相加。

## 最小调用组合

| 问题 | 首选 MCP 调用 | 按需补充 |
|---|---|---|
| 最新仓单及变化 | latest trading date + warehouse quantity | warehouse distribution |
| 临月仓单覆盖率 | contract info + actual-contract snapshot/timeseries + warehouse quantity | trading params |
| 持仓退出是否异常 | actual-contract timeseries + trading calendar | 历史同交割月合约 |
| 仓单地区集中度 | warehouse distribution | 仅在返回数量字段时计算 |
| 产业库存能否补货 | dzlabel 指标发现与时序 | 交易所公开资料 |
| 会员持仓集中度 | member positions | 仓单和价格结构交叉验证 |
| 完整交割风险 | 上述合约、持仓、仓单与库存调用 | Web Search 查询交易所规则、有效预报及历史实际交割量 |
