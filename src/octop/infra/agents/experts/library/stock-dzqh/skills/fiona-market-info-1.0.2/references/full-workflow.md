# 市场基础信息完整工作流程

按以下顺序执行，不要一开始同时调用所有 MCP。每次调用后先检查返回结果，再决定是否进入下一步。

## 第一步：识别客户意图

将问题归入以下一种或多种类型：

- **品种/合约/规则**：优先使用 `futures_market_data`。
- **交易日/交易时段**：只使用 `futures_market_data` 的交易日和合约规则工具。
- **行情快照/历史行情**：使用 `futures_market_data`。
- **板块或品种排名**：使用 `futures_ranking`。
- **沉淀资金、资金流向和投机度计算**：使用 `market_calculate`。
- **会员、波动率和仓单原始数据**：使用 `futures_market_data`。
- **综合基础信息**：按“标准化 → 行情 → 统计/计算”的顺序组合调用，不默认调用全部工具。

## 第二步：标准化品种、合约、日期和会员公司

1. 客户使用中文简称、别名、模糊代码或未指定交易所时，先调用 `futures_market_data` 的 `get_futures_product_info`，确认 `symbol`、品种名称、交易所和板块。
2. 客户询问指定合约时，确认 `contract` 与 `symbol` 是否匹配；不能把品种代码直接当作合约代码。
3. 客户说“最新”“今天”“上一交易日”时调用 `get_latest_futures_trading_date`（无必填参数）；客户问未来第 N 个交易日时调用 `get_next_futures_trading_date(target_date, n)`。
4. 客户问一段日期内的交易日时调用 `get_futures_trading_calendar(start_date, end_date, limit)`，并使用返回的实际交易日构造后续查询区间。
5. 客户提到会员公司（如"永安""中信""国泰君安"等）时，先调用 `get_futures_member_company_names` 进行模糊匹配，确认标准化会员名称后再传入后续查询。
6. 标准化失败或返回多个可能对象时，先说明歧义并缩小查询范围，不直接进入行情、排名或计算调用。

## 第三步：按客户场景调用工具

### A. 查询交易规则或可交易合约

1. 先完成第二步的品种和日期标准化。
2. 查询指定日期可以交易的合约时调用 `get_tradable_futures_contracts(date, symbol, limit)`；`date` 和 `symbol` 是必填条件。
3. 查询合约基础规则时调用 `get_futures_contract_info_table(contract, limit)`。
4. 查询合约在某日的交易参数时调用 `get_futures_contract_trading_params(contract, date)`；日期为空时以接口默认最新口径为准。
5. 只回答接口返回的乘数、最小变动价位、交割和交易时段等字段；不要凭记忆补充保证金、手续费或规则解释。

### B. 查询行情快照或历史行情

1. 查询当前或最近快照时调用 `get_futures_snapshot_quotes(symbol, contract, limit)`；`symbol` 和 `contract` 至少明确一个。
2. 查询指定真实合约历史时调用 `get_futures_timeseries_quotes(start_date, end_date, symbol, contract, frequency, limit)`，明确 `contract` 或 `symbol`、日期区间和频率。
3. 查询品种主力历史时调用 `get_futures_dominant_quotes(start_date, end_date, symbol, frequency, limit)`，并保留返回的实际主力合约代码。
4. 客户没有要求历史、排名、持仓或资金时，不调用 `futures_ranking` 或 `market_calculate`。
5. 主力历史超过单次返回限制时按日期分段，按日期和真实合约去重后再拼接；任何一段被截断都要降低结论范围。

### C. 查询板块、品种或主力排名

1. 先调用 `futures_ranking.get_ranking_indicators(limit)` 确认可用指标；客户已明确指标时可跳过枚举查询。
2. 按指定指标和日期排名时调用 `futures_ranking.get_product_ranking(indicator, date, symbol, order, limit)`；`order` 使用 `asc` 或 `desc`。
3. 查询板块或品种区间统计时调用 `futures_ranking.get_section_statistics(start_date, end_date, section, limit)`。
4. 查询主力合约横截面变化时调用 `futures_ranking.get_dominant_cross_section_change(symbol, date, periods, percentile_years, limit)`；查询单品种概览时调用 `futures_ranking.get_symbol_overview(symbol, date, history_years, sections)`。
5. 排名结果如果返回总数、返回数和截断状态，必须读取并记录；不能用被截断的结果声称全市场排名。

### D. 查询全市场成交持仓、沉淀资金、资金流向和投机度

1. 全市场成交持仓数量或金额使用`market_calculate.get_type_positions_amount(start_date, end_date, symbol, contract, limit)`
2. 沉淀资金、资金流向或投机度使用 `market_calculate.get_product_fund_flow(start_date, end_date, symbol, limit)`、`market_calculate.get_product_speculation(start_date, end_date, symbol, limit)`。

### E. 查询会员、波动率和仓单原始数据

1. 只有客户指定会员名称、需要名称标准化或结果需要名称映射时，才调用 `get_futures_member_company_names`。
2. 查询会员持仓排名调用 `get_futures_member_positions(start_date, end_date, symbol, contract, member_name, position_type, limit)`，至少明确交易日期和品种/合约；需要会员筛选时再传标准化的 `member_name`。
3. 查询波动率调用 `get_futures_volatility`；查询仓单数量或地区分布调用 `get_futures_warehouse_quantity`、`get_futures_warehouse_distribution`。
4. 这些结果在本 skill 中只作为原始事实展示，不自行计算集中度、逼仓风险或供需结论。

## 第四步：组合调用和停止条件

- 只问一个事实时，完成对应 MCP 调用并停止，不为凑“综合分析”追加其他 MCP。
- 同时问“合约 + 行情”时：标准化 → 交易规则/可交易合约 → 快照或历史行情。
- 同时问“行情 + 排名”时：标准化 → 行情数据 → `futures_ranking` 排名或截面工具。
- 同时问“行情 + 资金/持仓”时：标准化 → `futures_market_data` 基础行情/会员/仓单 → `market_calculate` 计算工具。
- 同时问“合约 + 行情 + 排名 + 资金”时：按上述顺序逐组调用，并在结果中分开标注数据来源。
- 当客户目标已经回答、数据为空、权限失败或继续调用不会增加证据时停止。

## 第五步：结果校验与输出

1. 每个 MCP 结果都核对实际数据日期、品种/合约、交易所和单位；如果返回 `total`、`returned`、`truncated` 或 `hint`，再检查这些字段，不自行补造缺失字段。
2. 发现日期、单位、合约或统计对象不一致时，不合并成一个结论，先说明口径差异。
3. 先写事实和数据口径，再写对比和排序；不把排名、持仓或资金变化直接解释成未来涨跌方向。