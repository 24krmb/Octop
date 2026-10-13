---
name: finoview-reports
version: "1.0.3"
display_name: 繁微 Fiona 报告与观点资料整理
display_name_en: Finoview Reports and Viewpoints
description_zh: 使用东证繁微正式研报、研究员观点、动态快评及用户附件，检索并提取作者、日期、材料元数据、原文数据和相关段落，按时期、作者或材料整理对照结果并保留原文出处。
description_en: Search Finoview official research reports, analyst viewpoints, market commentaries, and user-provided files; extract authors, dates, metadata, source data, and relevant passages; and organize comparisons by period, author, or material while preserving source attribution.
description: 繁微 Fiona 报告与观点资料整理。用于检索、理解、提炼和比较东证繁微正式研报、研究员观点、动态快评及用户附件，并保留原文依据。用户询问研报内容解读、观点变化、作者分歧、关键数据、研究逻辑、风险因素、材料详情或多份材料对照时使用。report 和 viewpoint MCP 当前公开免鉴权，无需访问凭证。不用于期货行情、基本面时序指标、技术面或新闻检索。
allowed-tools: Read, Grep, Glob, mcp__report__report_get_enums, mcp__report__report_search, mcp__report__report_get_detail, mcp__report__report_get_url, mcp__viewpoint__viewpoint_get_enums, mcp__viewpoint__viewpoint_search_views, mcp__viewpoint__viewpoint_get_weekly, mcp__viewpoint__viewpoint_search_dynamics, mcp__viewpoint__viewpoint_get_dynamic_detail
---

# 繁微 Fiona 报告与观点资料整理

本 Skill 由原 `finoview-reports`（正式研报）与 `finoview-viewpoint`（研究员观点与快评）合并而成，统一通过两个 MCP server 获取研究材料：

- `report`（`/mcp/report`）：正式研报 — 搜索、详情、PDF URL、枚举。
- `viewpoint`（`/mcp/viewpoint`）：研究员观点与快评 — 周度/定期观点、研究员观点、快评搜索与详情。

核心定位是**研究材料的理解与比较**：从研报、观点、快评及用户附件中提炼核心结论、关键数据、研究逻辑和风险，支持不同时期、作者、材料之间的比较，并保留原文依据。

> **架构变更（2026-08）**：原 `dzviewpoint` 已拆分为 `report` 和 `viewpoint` 两个独立 MCP server；原 `finoview-viewpoint` skill 的能力已并入本 Skill。
>
> **版本变更（v1.0.2，2026-09）**：`report_search` 优先使用结构化字段检索（`product_name` / `author` / `industry_name` / `forcast_value` / `rating_value` / 日期窗口）；`keyword` 搜索范围由「标题 + 摘要」收窄为**仅匹配研报标题**（搜索摘要会导致接口超时），仅作兜底使用，未命中时不反复换词试探。
>
> **版本变更（v1.0.3，2026-09）**：`report_search` 新增定期报告期次参数 `f_year`/`f_type`/`f_date_num`（仅适用于半年报/年报/季报/月报/周报等定期属性报告，搜索定期报告优先使用、禁止用日期模拟期次；泛指年份时禁用 `f_year`、改用日期窗口）；新增 `report_type_id`；评级枚举由 20-60 改为 1-5（`rating_value`/`forcast_value` 同义，传其一即可，旧值自动换算）；返回的 `rating_value`/`forcast_value` 改为按品种的评级列表；`report_get_enums` 新增 `periodic_types`。

## 前置条件与鉴权

本 Skill 依赖 MCP server `report` 和 `viewpoint`。首次调用前检查相关工具是否已就绪；工具缺失时，先按 `templates/` 中对应平台的配置添加两个 MCP server。

`report` 和 `viewpoint` 当前是公开免鉴权端点，**无需访问凭证**，配置时不要添加 `Authorization` 请求头。配置完成后分别调用 `report_get_enums` 和 `viewpoint_get_enums` 做最小健康检查；连接失败、超时或 transport error 时检查 MCP URL 和网络。若未来服务端改为需要鉴权，以最新接入文档为准，不预先要求用户配置凭证。

## 意图路由

| 用户意图 | 数据源 | 调用策略 |
| --- | --- | --- |
| 品种/作者/关键词/最新/评级/板块研报 | report | `report_search(...)`，结构化字段优先（含 `f_*` 期次参数）、keyword 兜底，流程见 `modules/search-strategy.md` |
| 某年某期定期报告（半年报/年报/季报/月报/周报） | report | `report_search(f_year + f_type + f_date_num)` 精确到期次；禁止用日期窗口模拟期次 |
| 某年份/时间段内全部报告（未指定定期类型） | report | `report_search(start_date + end_date)` 按归档时间筛选；**禁止用 `f_year` 泛指年份**（非定期报告无期次属性，会大量漏检） |
| 这篇研报具体说了什么 | report | `report_get_detail(report_id=...)` |
| 下载/获取研报文件/URL | report | `report_get_url(report_id=...)` |
| 本周/某周观点 | viewpoint | `viewpoint_get_weekly(year, week_num, ...)` |
| 月度/季度/半年/年度观点 | viewpoint | `viewpoint_search_views(freq + year + period)` |
| 某研究员最近怎么看 | viewpoint | `viewpoint_search_views(researcher_name=...)` |
| 最近有什么快评/快评详情/有图吗 | viewpoint | `viewpoint_search_dynamics` / `viewpoint_get_dynamic_detail(source_id=...)` |
| 有哪些研究员/xxx研究员介绍 | report + viewpoint | 两个 server 的 `get_enums` 取 `researchers`，详见全局约束 10 |
| 提炼/比较多份材料（研报、观点、快评、附件） | report + viewpoint + Read | 先按搜索策略取材料，再按 `modules/analysis-and-comparison.md` 提炼与比较 |

完整搜索流程见 `modules/search-strategy.md`，参数签名见 `references/api-spec.md`。

## 全局约束

1. 始终通过 MCP 调用 `mcp__report__*` / `mcp__viewpoint__*`，禁止自行构造 curl/httpie 请求。
2. 搜索默认 `limit=10`；用户未要求扩大范围时不要批量分页。`viewpoint_search_views` 必须补齐频率、年份和周期参数。`report_search` 优先使用结构化字段（期次 `f_year`/`f_type`/`f_date_num`、`product_name` / `author` / `industry_name` / `report_type_id` / `rating_value` / 日期窗口）；`f_*` 期次参数**仅适用于定期属性报告**（半年报/年报/季报/月报/周报），搜索定期报告**必须用 `f_*` 精确到期次、禁止用日期窗口模拟期次**（归档时间与所属期不一致，实测漏约 70% 数据）；用户泛指「某年的报告」等未指定定期类型时，用 `start_date`/`end_date` 日期窗口筛选，**禁止用 `f_year` 泛指年份**（非定期报告无期次属性，用 `f_year` 会漏掉大量报告）；`keyword` 仅匹配研报标题（v1.0.2 起）、仅作兜底。
3. 搜索结果摘要/文本可能截断为 200 字；用户问"具体说了什么"时必须调用 `report_get_detail` 或 `viewpoint_get_dynamic_detail`。
4. 品种评级映射：1=强烈看涨、2=看涨、3=震荡、4=看跌、5=强烈看跌（旧值 20-60 已废弃、后端自动换算）；`rating_value` 与 `forcast_value` 筛选同一字段，传其一即可。评级枚举以 `report_get_enums` 的 `ratings` 返回为准，不硬编码。搜索/详情返回的 `rating_value`/`forcast_value` 是**列表**（每项含 `product_name`、`futures_variety`、`variety_rating`、`rating_label`），按「品种名 → 评级中文（rating_label）」逐项渲染，如「黄金：看涨；白银：震荡」；无评级时为空列表。
5. "看涨"需要同时查询 rating_value=1 和 2；"看跌"需要同时查询 4 和 5。命中条件：研报关联的任一品种评级匹配。
6. 用户输入的作者/研究员姓名模糊或可能有错别字时，先调用 `report_get_enums` 或 `viewpoint_get_enums` 取 `researchers` 字段匹配正确姓名，再搜索。
7. 查询"本周"观点时先按当前日期确定年份和周数；若当前周返回空结果，依次回看最近 1–2 个已结束周，并明确报告实际周数和"当前周暂无数据"，不要把空结果表述为没有观点。
8. **快评展示与渲染**：
   - `viewpoint_search_dynamics` 返回的每条 item 含 `pictures`（图片 URL 数组）、`link`（关联链接 URL）。列表中有 pictures → 标注 `📷 有N张图片`；有 link → 标注 `🔗 有链接`，仅提示存在、不自动下载。
   - 用户说"看看图片"、"有图吗"、"展开看看"时，调用 `viewpoint_get_dynamic_detail(source_id=...)` 获取完整文本及图片/链接 URL。Agent 拿到 URL 后自行判断是否下载渲染（可 HTTP 下载后内联展示，也可列出 URL），下载失败静默跳过。
9. 用户要求下载研报或获取研报文件链接时，使用已有 `report_id` 调用 `report_get_url(report_id=...)` 返回 PDF 下载 URL。若上下文无 `report_id`，先通过搜索定位目标报告。
10. **研究员名片增强**（研报 + 观点 + 快评三源合一）：
   - 用户问"有哪些研究员"时：
     a. 调用 `report_get_enums` 与 `viewpoint_get_enums`，取 `researchers` 字段合并去重（字段：`user_name`、`tags`、`report_group`、`introduce`、`one_tags`、`qualify_num`、`consult_num`）。
     b. 对每位研究员并行调用 `report_search(author=<user_name>, limit=1)` 获取最近 1 篇研报作为预览。
     c. 展示格式：姓名 + 板块品种 + 职称头衔 + 最近研报标题及日期（1 条预览）。末尾追问"想了解哪位研究员的更多产出？"
   - 用户问"xxx研究员介绍"或指定具体研究员时：
     a. 先从 `researchers` 字段匹配确认姓名和板块。
     b. 并行调用 `report_search(author=<姓名>, limit=3)`、`viewpoint_search_views(researcher_name=<姓名>, limit=3)`、`viewpoint_search_dynamics(keyword=<姓名>, limit=3)`。
     c. 展示格式：研究员基本信息（姓名、板块品种、简介、职称、从业资格号）→ "📄 最近研报"（3 条）→ "📝 最近观点"（3 条）→ "⚡ 最近快评"（3 条）。
     d. **提炼近期观点**：对每条材料从摘要/text 中提取 1 句核心判断（如"看多铜"、"目标价上调至 xxx"）附在标题和日期之后。若截断无法提取，调用 `report_get_detail(report_id=...)` 或 `viewpoint_get_dynamic_detail(source_id=...)` 补全后再提炼。

最终回答需区分研报/观点原文、接口筛选条件和 Agent 的归纳解释；不要将研究员观点表述为确定事实或投资建议。

## 理解与比较规范（核心）

材料取回后的提炼与比较遵循以下原则，完整流程见 `modules/analysis-and-comparison.md`：

1. **四维提炼**：每份材料按「核心结论 → 关键数据 → 研究逻辑 → 风险」四个维度提炼，缺哪一维就明确说缺，不虚构补齐。
2. **保留原文依据**：每条核心结论附原文引用（材料类型、标题、作者、日期、`report_id`/`source_id` 及原文摘句），区分「原文/接口内容」「Agent 归纳」「用户附件内容」，不把观点表述为确定事实或投资建议。
3. **先补全再提炼**：摘要/text 截断时，先调用详情接口取完整内容再提炼，禁止基于截断文本下判断。
4. **比较三轴**：支持按时期（同一作者/品种的时间线变化）、作者（不同研究员的分歧与共识）、材料类型（研报 vs 观点 vs 快评/附件的交叉验证与矛盾点）比较。
5. **附件同等对待**：用户直接提供的附件（PDF/文档/图片）用 Read 读取后视为一种研究材料，同样四维提炼并纳入比较；附件内容与 MCP 材料冲突时如实并列呈现，不擅自取舍。

## 辅助文件

| 文件 | 用途 |
| --- | --- |
| `modules/search-strategy.md` | report + viewpoint 全部搜索流程 |
| `modules/analysis-and-comparison.md` | 四维提炼、比较框架、原文依据规范 |
| `references/api-spec.md` | 两个 MCP server 的 tool 参数签名，调 tool 前先查此表 |
| `templates/` | 各平台 MCP 配置参考（同时含 report 与 viewpoint） |

## 示例问题

- "铜最近有什么正式研报和快评？选一篇研报展开详情，提炼核心结论、关键数据、研究逻辑和风险，并标注原文依据。"
- "比较两位研究员对铜的看法差异，并分别给出原文依据。"

## 风险提示与免责声明

完成实质性回答后，根据本次输出内容附加一项固定提示，不得省略或改写：

- 仅查询、整理、计算或复述数据时，使用普通提示。
- 涉及方向、趋势、强弱、结构含义、影响、情景、风险、原因推断或交易决策时，使用加强提示；不得承诺收益或替用户决策。
- 配置、报错和澄清问题无需提示。

> 风险提示：本内容由 AI 根据可用数据和材料生成，少量数据处理流程及研究框架来自于东证衍生品研究院；AI 生成内容不代表东证衍生品研究院及其研究人员的观点，也未经其审核或背书。数据可能存在延迟、缺失或处理误差，请核对原始来源。本内容仅供信息参考和研究辅助，不构成投资建议。


提示置于回答及可展示产出物末尾，不替代正文中的数据来源、时点、口径和局限说明；结构化产出使用 `risk_level` 和 `risk_disclaimer` 字段携带同一提示。
