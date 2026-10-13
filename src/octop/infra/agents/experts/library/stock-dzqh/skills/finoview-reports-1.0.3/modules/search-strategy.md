# 研究材料搜索策略（report + viewpoint）

两份材料的搜索流程已合并：正式研报走 `report` server，观点与快评走 `viewpoint` server。调用前先查 `references/api-spec.md` 确认参数签名。

**研报检索优先级（v1.0.3）**：`report_search` 优先使用结构化字段——期次 `f_year`/`f_type`/`f_date_num`（定期报告）、品种 `product_name`、作者 `author`、行业 `industry_name`、报告类型 `report_type_id`、评级 `rating_value`（1-5，与 `forcast_value` 同义）、时间窗口 `start_date` / `end_date`、排序 `sort_order`；`keyword` 仅匹配研报标题且易触发超时，只在结构化字段无法表达需求时兜底使用，不作为主检索手段。

## GET_ENUMS

触发："有哪些报告类型/行业分类/品种列表/评级/预测""有哪些观点板块""快评分类""研究员列表"。

- 研报相关：调用 `report_get_enums`，按 key 取 `types`（报告类型）、`industries`（行业/板块）、`futures`（期货品种）、`ratings`（品种评级，1-5）、`forcasts`（与 `ratings` 一致）、`researchers`（研究员列表）、`periodic_types`（定期报告类型，含 `f_type` 与 `f_date_num` 语义描述）。
- 枚举值动态读取、不硬编码：评级映射以 `ratings` 返回为准；定期报告 `f_type`/`f_date_num` 语义以 `periodic_types` 返回为准。
- 观点相关：调用 `viewpoint_get_enums`，按 key 取 `categories`（观点板块）、`catalogues`（快评分类）、`researchers`（研究员列表）。

两个 `researchers` 字段结构一致（user_id, user_name, tags, report_group, introduce, one_tags, qualify_num, consult_num），需要全景列表时合并去重。

## SEARCH_BY_PRODUCT

触发："黄金最近有什么研报""铜的报告"。

1. 调用 `report_search(product_name=..., limit=10)`。
2. 无结果时降级为 `keyword=...` 再搜索一次（v1.0.2：`keyword` 仅匹配标题，使用归一化后的品种名）。
3. 展示标题、作者、发布日期、摘要、`report_id`；评级为列表，逐项渲染"品种名 → 评级中文（rating_label）"（如"黄金：看涨"），无评级为空列表、不展示。

## PERIODIC_REPORT

触发："2025 年下半年半年报""2025 年年报""2025 年一季度季报""2025 年 12 月月报""某周周报"。**仅当用户明确指定定期报告类型时走此流程**；泛指"2026 年的报告""某时间段内的报告"走 SEARCH_BY_DATE_RANGE，不得用 `f_year`。

1. 使用 `report_search(f_year=..., f_type=..., f_date_num=...)` 精确到某年某期；`f_type`：1=周度、2=月度、3=季度、4=半年、5=年度；`f_date_num` 语义（季度 1-4、半年 1=上半年/2=下半年、月度 1-12、周度周数 1-53、年度=1）先查 `report_get_enums` 的 `periodic_types`，不硬编码。
2. 搜索某类型全部报告（不限期次）时用 `report_type_id`（如半年报=120448），可与 `f_*` 叠加。
3. **禁止用 `report_type_id` + `start_date`/`end_date` 模拟期次**：实际归档时间与所属期不一致，实测会漏掉约 70% 数据，必须使用 `f_*` 参数。
4. **`f_*` 仅适用于定期属性报告**：用户泛指"某年的报告"（未指定定期类型）时禁用 `f_year` 筛选——非定期报告（日度点评/深度报告等）无期次属性，`f_year=2026` 会漏掉大量报告。

## SEARCH_BY_DATE_RANGE

触发："2026 年的报告""最近三个月有什么研报""某时间段内的报告"（未指定定期报告类型）。

1. 使用 `report_search(start_date=..., end_date=...)` 按归档时间筛选（YYYYMMDD）。
2. **禁止用 `f_year` 泛指年份**：`f_*` 期次参数仅匹配定期属性报告（半年报/年报/季报/月报/周报），非定期报告无期次属性，会被大量漏检。

## SEARCH_BY_AUTHOR

触发："某作者最近有什么研报"。

1. 姓名不确定或有错别字时，先调用 `report_get_enums` 取 `researchers` 字段匹配正确姓名。
2. 使用匹配后的姓名调用 `report_search(author=..., limit=10)`。
3. 用户追问具体内容时，针对选中的 `report_id` 调用 `report_get_detail`。

## SEARCH_BY_RATING

用户说"看涨"时分别使用 `rating_value=2` 和 `rating_value=1`（1=强烈看涨）；说"看跌"时分别使用 4 和 5，合并去重后再展示。`rating_value` 与 `forcast_value` 筛选同一字段、传其一即可，旧值 20-60 后端自动换算；评级语义以 `report_get_enums` 的 `ratings` 返回为准，不硬编码。命中条件：研报关联的任一品种评级匹配。

## LATEST

"最近有什么新研报"使用 `report_search(sort_order="desc", limit=10)`，只有用户指定品种、行业或评级时再增加筛选条件。

> 注意：旧版 `viewpoint_get_latest_reports` 已删除，统一用 `report_search(sort_order="desc")` 替代。

## SEARCH_BY_KEYWORD

仅当关键词无法映射为品种 / 作者 / 板块等结构化字段时，才使用 `report_search(keyword=..., limit=10)`；能映射的一律优先结构化字段。**`keyword` 仅匹配研报标题、不含摘要（v1.0.2 起收窄），是最后手段而非默认选择**。关键词过宽时优先缩短为核心品种或主题词，不盲目分页；无结果说明标题未含该词，改用结构化字段检索，不反复换词试探。

## GET_DETAIL

只有上下文已有 `report_id` 或用户明确提供报告 ID 时调用 `report_get_detail`。搜索列表的 200 字摘要不能替代详情接口。

## GET_REPORT_FILE_URL

触发："下载这篇研报""给我这篇报告的 PDF 链接""获取研报文件"。

1. 确保上下文已有 `report_id`（来自搜索结果、最新研报列表或用户直接提供）。
2. 若无 `report_id`，先通过 `report_search` 定位目标报告。
3. 调用 `report_get_url(report_id=...)` 获取 PDF 下载 URL 并返回给用户。

## SEARCH_BY_RESEARCHER

触发："某研究员有什么观点""张三最近怎么看"。

1. 姓名不确定时调用 `viewpoint_get_enums` 取 `researchers` 字段做匹配。
2. 使用 `viewpoint_search_views(researcher_name=..., limit=10)`。

## WEEKLY_VIEW

触发："本周观点""黄金这周怎么看"。

1. 按当前日期确定年份和周数，调用 `viewpoint_get_weekly(year=..., week_num=..., product_name=...)`。
2. 当前周返回空结果时，依次回看最近 1–2 个已结束周，并明确报告实际周数和"当前周暂无数据"。
3. 需要板块视角时先从 `viewpoint_get_enums` 取 `categories` 字段。

## PERIODIC_VIEW

触发："月度观点""Q2 季度观点""下半年展望"。使用 `viewpoint_search_views`，并传入 `freq`、`year`、`period` 和可选的 `product_name`。

## DYNAMIC_SEARCH

触发："最近有什么快评""重要的宏观快评"。需要分类时先从 `viewpoint_get_enums` 取 `catalogues` 字段，再用 `viewpoint_search_dynamics(keyword=..., catalogue=..., important=..., limit=10)`。

- `important` 参数类型为 int，1=重要，0=不重要。
- 列表中有 `pictures` → 标注 `📷 有N张图片`；有 `link` → 标注 `🔗 有链接`，仅提示、不自动下载。

## DYNAMIC_DETAIL

用户追问"这条快评具体说什么/有图吗"时，必须从列表结果取得 `source_id`，调用 `viewpoint_get_dynamic_detail(source_id=...)`。不能用研报的 `report_id` 代替。

## RESEARCHER_INTRO

触发："有哪些研究员""xxx研究员介绍"。完整流程见 SKILL.md 全局约束 10：

1. `report_get_enums` + `viewpoint_get_enums` 取 `researchers` 合并去重。
2. 列表模式：对每位研究员调用 `report_search(author=..., limit=1)` 取最近 1 篇研报预览。
3. 详情模式：并行调用 `report_search(author=..., limit=3)`、`viewpoint_search_views(researcher_name=..., limit=3)`、`viewpoint_search_dynamics(keyword=..., limit=3)`，分"📄 最近研报 / 📝 最近观点 / ⚡ 最近快评"三组展示。
4. 每条材料提炼 1 句核心判断；截断时用 `report_get_detail` / `viewpoint_get_dynamic_detail` 补全。
