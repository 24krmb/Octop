---
name: fiona-warehouse-delivery-pressure
version: "1.0.2"
display_name: 繁微 Fiona 仓单库存与交割数据
display_name_en: Fiona Warehouse Receipts and Delivery Data
description_zh: 使用注册仓单、指定交割库库存、有效预报、产业库存、临近交割合约持仓、合约期限和历史交割数据，统一数量与合约手数口径，计算仓单覆盖率、持仓保留率并整理同期对照结果。
description_en: Use registered warehouse receipts, designated delivery warehouse inventory, valid forecasts, industry inventory, nearby contract open interest, contract term structure, and historical delivery data; unify quantity and contract lot units; calculate warehouse receipt coverage ratios and position retention rates; and organize period-over-period comparison results.
description: 繁微 Fiona 仓单库存与交割数据。用于分析注册仓单、交割库库存、有效预报、产业库存、临月持仓、合约期限和历史交割水平，评估仓单覆盖、持仓滞留与潜在交割压力。用户询问仓单变化、库存与仓单关系、临月持仓、逼仓或挤仓风险、交割货源、仓单注销、有效预报或全市场交割压力时使用。dzlabel MCP 需要 API Key；futures_market_data 当前公开免鉴权。不把单一指标解释为已经发生的逼仓，也不提供交易建议。
---

# 繁微 Fiona 仓单库存与交割数据

## 前置条件与 API Key

本 Skill 依赖 `futures_market_data` 和 `dzlabel` 两个 MCP。首次调用前检查当前工具列表；工具缺失时，按 [MCP 接入与工具清单](references/mcp-endpoints.md) 和 `agents/openai.yaml` 只添加缺少的服务。

- `dzlabel` **需要 API Key**，实际以 `Authorization: Bearer <API Key>` 鉴权。
- `futures_market_data` 当前公开免鉴权，**不需要 API Key**，不要为它配置 `Authorization` 请求头。

API Key 申请：目前暂不支持在线自助申请，请联系繁微对口销售或项目联系人获取。

只在客户端凭证管理区保存真实 API Key，不得写入对话、Skill 文件或版本库。`401`/`403` 时检查 `dzlabel` 的 API Key 与权限；超时或 transport error 时检查对应 URL 和网络。

判断临近交割时，持仓退出速度、已确认仓单和潜在补货能力是否匹配。首次调用 MCP 数据前，必须读取 [MCP 接入与工具清单](references/mcp-endpoints.md)，完成依赖、端点及认证检查；已接入时无需重复配置。复杂分析读取 [仓单库存与交割压力研究规则](references/research-framework.md)；查询公开资料时参考 [数据源与工具规范](references/data-sources.md)。

## 工作原则

1. 明确品种、目标合约、观察日以及距离最后交易日和交割期的剩余时间。分析对象应是具体临近合约，不用主力合约或品种总持仓替代。
2. 区分注册仓单、指定交割库合格库存、有效预报和广义产业库存。它们处于不同转化阶段，除非来源明确证明互不重叠，不做简单加总。
3. 将仓单和库存统一换算为合约手数后再与持仓比较，同时核对交割单位、品级、品牌、地区、完税状态、仓单类型和有效期。
4. 判断异常持仓时按“距离最后交易日的相同交易日数”对齐历史合约，并优先比较相同交割月份和相同规则时期；不以单一固定阈值定义异常。
5. 同时观察已确认供给、潜在补货、持仓退出、历史实际交割和价格结构。低仓单覆盖率本身不等于逼仓，高仓单也不等于必然利空。
6. 先陈述数据事实，再给出库存压力、卖方交割压力和买方接货压力的情景判断。对缺失的有效预报、交割规则或实际交割量明确降级，不补造数据。

## 数据获取

- 使用 `futures_market_data` 的 `get_latest_futures_trading_date`、`get_futures_trading_calendar`、`get_futures_product_info`、`get_tradable_futures_contracts` 和 `get_futures_contract_info_table` 确认交易日、品种、目标实际合约与期限；用 `get_futures_snapshot_quotes` 或 `get_futures_timeseries_quotes` 获取目标合约行情和持仓。
- 使用 `get_futures_warehouse_quantity` 获取注册仓单、变化和服务端提供的折合手数，使用 `get_futures_warehouse_distribution` 获取仓库或地区信息；只有工具确实返回数量时才计算地区集中度。必要时调用 `get_futures_member_positions` 做会员持仓交叉验证。具体参数、限制和口径见 [MCP 接入与工具清单](references/mcp-endpoints.md)。
- 使用 `dzlabel` 的 `get_products` → `search_indicators` → `get_indicator_series` 调用链搜索社会库存、工厂库存、港口库存等广义库存；需要目录浏览时补充 `expand_catalog` 和 `get_indicators`。直接使用该 MCP，不依赖其他 Skill；每次选择与品种最相关的少数指标，检查单位、频率、统计范围和最新日期。
- 使用 Web Search 从交易所官网补充有效预报、指定交割仓库库存周报、交割规则、仓单有效期和历史实际交割量。优先交易所原始网页、PDF、Excel 或公告，并记录发布日期和统计口径。
- 单次仓单时序最多 60 个自然日、最多 3 个品种；更长历史分段查询、去重并按日期拼接。任何截面结果都检查是否截断。

## 数据整理重点

- **持仓滞留**：临月持仓、持仓保留率、临月持仓占比、移仓速度及其剩余期限对齐后的历史位置。
- **仓单保障**：注册仓单折合手数、仓单覆盖率、仓单变化及季节性位置。
- **补货能力**：有效预报、指定交割库合格未注册库存、可用库容和广义库存；可用库容不是库存。
- **实际交割基准**：历史交割量和交割转化率，用于区分最大潜在压力与常态交割需求。
- **确认信号**：近远月价差、现货升贴水、仓单地区和会员持仓集中度。只作交叉验证，不以单一信号定性。

## 输出

按问题自主裁剪，通常包括：结论、数据时点与口径、临月持仓状态、仓单与补货能力、产业库存背景、价格或集中度确认、风险情景及数据限制。明确区分：

- 库存与仓单充裕造成的供给或接货压力；
- 仓单不足且持仓滞留造成的卖方交割紧张；
- 数据不足但值得跟踪的潜在风险。

不把风险信号写成已经发生的逼仓，不推断具体会员或客户一定缺货，不给出无依据的买卖建议。商品期权不属于默认分析范围；只有临近期权行权可能显著改变目标期货合约持仓时才作为补充因素。

## 风险提示与免责声明

完成实质性回答后，根据本次输出内容附加一项固定提示，不得省略或改写：

- 仅查询、整理、计算或复述数据时，使用普通提示。
- 涉及方向、趋势、强弱、结构含义、影响、情景、风险、原因推断或交易决策时，使用加强提示；不得承诺收益或替用户决策。
- 配置、报错和澄清问题无需提示。

普通提示：

> 风险提示：本内容由 AI 根据可用数据和材料生成，少量数据处理流程及研究框架来自于东证衍生品研究院；AI 生成内容不代表东证衍生品研究院及其研究人员的观点，也未经其审核或背书。数据可能存在延迟、缺失或处理误差，请核对原始来源。本内容仅供信息参考和研究辅助，不构成投资建议。

加强提示：

> 风险提示：本内容由 AI 根据可用数据、材料和研究辅助流程生成，少量数据处理流程及研究框架来自于东证衍生品研究院；AI 生成内容不代表东证衍生品研究院及其研究人员的观点，也未经其审核或背书。数据、计算和表述可能存在延迟、缺失、口径差异、处理误差或不确定性，涉及的方向、情景、风险及影响不构成预测或保证。请核对原始资料和计算口径。本内容仅供信息参考和研究辅助，不构成投资研究报告、投资建议、投资咨询意见、交易依据或收益承诺。期货及衍生品交易风险较高，请独立、审慎决策。

提示置于回答及可展示产出物末尾，不替代正文中的数据来源、时点、口径和局限说明；结构化产出使用 `risk_level` 和 `risk_disclaimer` 字段携带同一提示。
