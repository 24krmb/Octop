# Fiona 期货资讯可选 MCP 接入与工具清单

## 目录

1. 连接与认证
2. 首次接入检查
3. 资讯工具
4. 经济日历工具
5. Web Search 核验与降级
6. 客户端模板

## 连接与认证

| MCP | URL | 作用 |
|---|---|---|
| `fiona-news` | `https://track.finoview.com.cn/fiona/mcp/news` | 重要资讯合集和品种标签资讯 |
| `fiona-economic-calendar` | `https://track.finoview.com.cn/fiona/mcp/economic_calendar` | 经济指标、计划事件和市场假期 |

两个端点的 Transport 均为 `streamable_http`，均使用活动 MCP 连接器的 Bearer Token，认证请求头格式为 `Authorization: Bearer <token>`。Token 由服务提供方授权，并配置在客户端或平台的凭证管理区；不得把真实 Token 写入 Skill、模板、版本库、日志或对话。除非服务提供方明确说明两个端点共用凭证，否则分别按各端点授权信息配置。

这两个 MCP 都是可选增强，不在 `agents/openai.yaml` 中声明为安装依赖。未配置时直接使用 Web Search，不提示用户安装，也不阻止 Skill 执行。用户明确选择启用时，使用本包模板，并只合并缺失的 server 项，不覆盖用户已有 MCP 配置。

## 首次接入检查

仅在用户选择启用 MCP，或当前工具列表已经提供相关工具时执行本节。不要为了普通资讯任务主动探测端点、索取 Token 或暂停 Web Search。是否已接入由当前工具列表判断，不在 Skill 包内保存 `is_configured` 一类状态。

1. 只检查用户选择启用的服务；启用 `fiona-news` 时，至少应提供 `get_fino_ai_collection` 和 `get_fino_news_ai_tagged`。
2. 启用 `fiona-economic-calendar` 时，至少应提供 `get_economic_indicators`、`get_economic_events`、`get_market_holidays` 和 `get_economic_indicator_detail`。
3. 用户明确选择启用但工具缺失时，说明缺少的服务，通过 MCP 配置页或下方客户端模板完成配置。修改现有配置前须征得用户同意。
4. 引导用户在客户端安全凭证区配置服务方提供的 Token；不要要求用户在对话中发送 Token。配置后重新加载 MCP 工具，并用当前任务所需的最小查询确认授权和返回正常。

工具不存在通常表示尚未安装或未重新加载；HTTP `401`/`403` 表示 Token 或权限问题；超时和 Transport 错误应检查 URL、网络和客户端支持。一个服务失败不应伪装为另一个服务的数据。

## 资讯工具

### `get_fino_ai_collection`

仅在全市场宽扫描、公开检索召回不足或需要交叉检查时，用于补充最近 24 小时的候选事件；普通任务不必调用。传入与报告一致的明确起止时间，跨度不得超过 24 小时。合并重复快讯，检查发布时间，不声称该合集覆盖全部市场。

### `get_fino_news_ai_tagged`

仅在公开检索结果较少或需要交叉检查时，用于具体品种资讯召回；不要作为默认查询。传入用户已明确或经可靠来源确认的品种代码和时间范围；无法可靠判断代码时先核实，不猜造映射。单次跨度不得超过 7 天、品种不得超过 10 个。

品种标签、重要性标签和快讯正文只用于发现线索，不能独立证明真实性、品种相关性、因果关系或影响方向。事故、停产、制裁、政策核查和主题事件发展脉络必须另查官方或可靠公开来源。

## 经济日历工具

- `get_economic_indicators`：查询已公布或待公布的宏观指标及前值、预测值和公布值。
- `get_economic_events`：查询央行、政府和官员讲话等计划事件。
- `get_market_holidays`：查询近期市场假期；具体期货交易所休市和交易时段调整以交易所公告为准。
- `get_economic_indicator_detail`：取得指标解释、历史值或下次公布时间；先从指标列表取得 `data_id`。

经济日历的结构化字段可作为宏观日历任务的可靠数据源，并可与 Web Search 并行调用。它适合搭建事件表，但不替代政策含义、统计原文、事件背景、市场反应或交易安排所需的进一步来源。

## Web Search 核验与降级

Web Search 是默认主路径。资讯 MCP 的候选事件仍须通过公开网页核对事件时间、发布日期和正文，并为重要事实提供可靠链接。搜索摘要同样只用于发现线索。

MCP 调用失败、超时、未授权、返回为空或不覆盖目标时间时，直接继续 Web Search。只有用户明确要求 MCP 数据，或缺失明显影响报告范围时才简要披露；不得因 MCP 失败而补造快讯、指标或日历事件。

## 客户端模板

仅当用户选择启用时，按客户端选取对应模板，将其中所需的一个或两个 server 配置合并到用户现有配置：

- Claude：`../templates/claude/mcp.json`
- OpenCode：`../templates/opencode/mcp.json`
- OpenClaw：`../templates/openclaw/mcp.json`
- WorkBuddy：`../templates/workbuddy/mcp.json`

模板中的 `<your-authorized-mcp-token>` 是占位符，只能在本地安全配置中替换，不能提交包含真实 Token 的模板。
