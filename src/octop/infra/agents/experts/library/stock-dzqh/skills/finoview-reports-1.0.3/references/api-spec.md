# 研究材料 API 参考

本 Skill 使用两个 MCP server：`report`（端点 `/mcp/report`）和 `viewpoint`（端点 `/mcp/viewpoint`）。底层调用必须通过 MCP（`mcp__report__*` / `mcp__viewpoint__*`），不得自行构造 HTTP 请求。

## report server（正式研报）

| MCP tool            | 用途                                            | 关键参数                                                                                                                                       |
| ------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `report_get_enums`  | 全部枚举聚合（类型/行业/品种/评级/研究员/定期报告类型） | 无                                                                                                                                         |
| `report_search`     | 核心研报搜索（含最新研报，sort_order="desc"）   | keyword(仅匹配标题), author, product_name, industry_name, report_type_id, rating_value(1-5), forcast_value(与rating_value同义), f_year, f_type, f_date_num, start_date, end_date, sort_order(默认"desc"), limit(默认10), offset |
| `report_get_detail` | 单篇研报完整详情                                | report_id                                                                                                                                      |
| `report_get_url`    | 研报 PDF 下载 URL                               | report_id                                                                                                                                      |

`report_get_enums` 返回 7 个字段：
- `types` — 报告类型枚举
- `industries` — 行业/板块枚举
- `futures` — 期货品种枚举
- `ratings` — 品种评级枚举（1=强烈看涨, 2=看涨, 3=震荡, 4=看跌, 5=强烈看跌；旧值 20-60 已废弃，后端自动换算）
- `forcasts` — 与 `ratings` 内容完全一致（两者筛选同一字段）
- `researchers` — 研究员列表（各含 user_id, user_name, tags, report_group, introduce, one_tags, qualify_num, consult_num）
- `periodic_types` — 定期报告类型：`[{f_type, f_type_name, f_date_num_desc}]`，如 `{1, 周度, 周数(1-53)}`、`{2, 月度, 月份(1-12)}`、`{3, 季度, 1-4 分别代表第一至第四季度}`、`{4, 半年, 1=上半年 2=下半年}`、`{5, 年度, 1}`

### `report_search` 入参要点（全部可选）

- **定期报告期次（v1.0.3 新增，仅适用于定期属性报告）**：`f_year`（年份，如 2025）+ `f_type`（1=周度, 2=月度, 3=季度, 4=半年, 5=年度）+ `f_date_num`（期次：季度=1-4；半年=1 上半年/2 下半年；月度=1-12；周度=周数 1-53；年度=1）。三者建议搭配使用；语义以 `report_get_enums` 的 `periodic_types` 返回为准，不硬编码。**仅当用户明确指定定期报告类型时使用**；泛指「某年份的全部报告」时不得用 `f_year`（非定期报告无期次属性，会大量漏检），应改用 `start_date`/`end_date` 日期窗口。
- **禁止用日期模拟期次**：不要用 `report_type_id` + `start_date`/`end_date` 模拟"某年下半年"等期次筛选——实际归档时间与所属期不一致，实测会漏掉约 70% 数据，必须使用 `f_*` 参数。
- `report_type_id`（int）：报告类型 ID（如半年报=120448），搜索某类型全部报告时使用，可与 `f_*` 叠加。
- **评级筛选（v1.0.3 语义变化）**：`rating_value` / `forcast_value` 取值 1-5（1=强烈看涨, 2=看涨, 3=震荡, 4=看跌, 5=强烈看跌），两者筛选同一字段、**传其一即可**；旧值 20-60 仍兼容（后端自动换算）。命中条件：研报关联的任一品种评级匹配。
- `keyword` 仅匹配研报标题、不含摘要；`start_date`/`end_date` 为归档时间维度（YYYYMMDD），不等于定期报告所属期。

### `report_search` / `report_get_detail` 出参要点

- `rating_value` / `forcast_value` 为**列表**（两者内容完全相同），每项 `{"product_name", "futures_variety", "variety_rating", "rating_label"}`。一篇研报可关联多个品种、各品种评级不同；无评级时返回 `[]`。
- 渲染时按"品种名 → 评级中文（rating_label）"逐项展示，例如"黄金：看涨；白银：震荡"。

## viewpoint server（观点与快评）

| MCP tool                       | 用途                                                                   | 关键参数                                                                                                          |
| ------------------------------ | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `viewpoint_get_enums`          | 全部枚举聚合（板块分类/快评分类/研究员列表）                           | 无                                                                                                                |
| `viewpoint_search_views`       | 定期观点搜索（合并原按研究员查 + 按周期查）                            | researcher_name, freq(monthly/quarterly/semiannually/annually), year, period, product_name, limit(默认50), offset |
| `viewpoint_get_weekly`         | 周度板块观点                                                           | year(默认2026), week_num(默认27), category_id, product_name                                                       |
| `viewpoint_search_dynamics`    | 快评搜索（返回 pictures URL + link URL）                               | keyword, catalogue, important(1/0), start_date, end_date, limit(默认10), offset                                   |
| `viewpoint_get_dynamic_detail` | 快评详情（多模态：完整文本 + pictures URL + link URL，Agent 自行渲染） | source_id                                                                                                         |

`viewpoint_get_enums` 返回 3 个字段：
- `categories` — 观点板块分类
- `catalogues` — 快评分类
- `researchers` — 研究员列表（字段结构同 report server）

## 参数注意事项

- `report_search` 优先使用结构化字段（期次 `f_year`/`f_type`/`f_date_num`、`product_name` / `author` / `industry_name` / `report_type_id` / `rating_value` / 日期窗口 / `sort_order`）；`keyword` 仅匹配研报标题、不含摘要（搜索摘要会导致接口超时），仅作兜底，无结果时改用结构化字段、不反复换词。
- 搜索定期报告（半年报/年报/季报/月报/周报）必须用 `f_year`+`f_type`+`f_date_num` 精确到期次，禁止用日期窗口模拟期次（归档时间与所属期不一致，实测漏约 70% 数据）。
- `f_*` 期次参数仅适用于定期属性报告；用户泛指「某年的报告」（未指定定期类型）时禁用 `f_year`，必须用 `start_date`/`end_date` 日期窗口，否则非定期报告（无期次属性）会被大量漏检。
- `viewpoint_search_dynamics` 的 `important` 参数为 int 类型：1=重要，0=不重要。
- `viewpoint_get_dynamic_detail` 返回多模态内容（完整文本 + 图片/链接 URL），Agent 自行判断是否下载渲染，下载失败静默跳过。
- 快评详情的 `source_id` 与研报的 `report_id` 不通用，不可混用。

## 已删除的旧接口

以下接口已从后端删除，MCP 不再暴露，Skill 中不得引用：
- `GET /report/latest`、`viewpoint_get_latest_reports` → 用 `report_search(sort_order="desc")` 替代
- `viewpoint_get_report_types` / `get_industries` / `get_futures` / `get_ratings` / `get_forcasts` → 合并入 `report_get_enums`
- `viewpoint_get_view_researchers` → 合并入 `report_get_enums` 的 `researchers` 字段
- `viewpoint_get_view_categories` → 合并入 `viewpoint_get_enums` 的 `categories` 字段
- `viewpoint_get_dynamic_catalogues` → 合并入 `viewpoint_get_enums` 的 `catalogues` 字段
- `GET /view/periodic`、`GET /view/by_researcher`、`viewpoint_get_periodic_viewpoint`、`viewpoint_get_view_by_researcher` → 用 `viewpoint_search_views` 替代
