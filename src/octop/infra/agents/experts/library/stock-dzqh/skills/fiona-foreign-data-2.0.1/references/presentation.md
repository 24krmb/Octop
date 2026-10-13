# HTML 交付

本页用于假期／自定义区间报告；盘前专属图表按 [盘前预警规则](pre-market-warning.md) 组织，不将其强套为 holiday 场景。

使用 `assets/report.html` 和 `assets/report.css`，通过 `scripts/render_report.py` 将已核验资料生成单文件 HTML。无第三方字体、脚本、图表 CDN 或浏览器端 MCP 调用，可离线打开；引用链接联网后可访问。报告是生成时快照，不暗示实时刷新或网页内可与 AI 聊天。

## 生成

整理 JSON 底稿后执行：

```sh
python3 scripts/render_report.py /absolute/path/report-data.json /absolute/path/report.html
```

路径相对于本技能目录。脚本仅依赖 Python 标准库。它不会取数、验证新闻或决定合约可比性；这些由研究过程负责。它验证重复标的、时间边界、有限数值与正基准，并由底稿两端价格计算图表和主表的同一涨跌幅。它无法从数值识别原始价或聚合价，填入前必须核实 `base`、`last` 是同口径原始端点，不能来自分桶序列。未满足排名条件的项只列明细。不要从演示 JSON 中沿用任何行情或事件。

`assets/demo.json` 是合成样式样本，`demo: true`；所有标的、价格、日期、观察文字均为演示，不是历史报告或 MCP 成功调用证明。真实报告使用 `demo: false`，真实来源和可核实时间，不能只去掉演示标记。

使用真实近期行情测试时，设置 `demo: false`、`scenario: "custom_interval"`；若明确假设国内休市则用 `scenario: "simulated_holiday"`。两者仍须真实调用行情和核实新闻，不能用合成 demo.json 替代。后者会在首屏标注模拟休市假设；它不验证官方假期日历选择、节前夜盘或真实复市反应，这些须在实际假期或有同口径历史资料时另行验收。

## 底稿字段

- `title`、`subtitle`：本期标题和一句观察范围；不承诺覆盖全球全部资产。
- `scenario`：`holiday`（默认实际假期）、`custom_interval`（自定义区间）、`simulated_holiday`（国内休市假设）。后两种标题分别使用“自定义区间外盘观察”“假期场景模拟”，不虚构法定假期名称。
- `endpoint_mode`：整份报告统一的端点口径，独立于 scenario。`pre_window_anchor`（未传时默认，兼容旧底稿）要求 `base_time <= requested_start <= last_time <= requested_end` 且两端时刻不同；`in_window` 要求 `requested_start <= base_time < last_time <= requested_end`，用于周报和用户要求的窗口内首末原始统计。未知值报错，不隐式放宽。两种模式均只接受已核实原始价格。渲染器自动在首屏、方法说明和底稿写入口径，不靠标题推断。
- `demo`：布尔值；`generated_at`、`requested_start`、`requested_end`、`news_cutoff`：带时区 ISO 8601。观察截止不得晚于生成时间。`sync_at`：服务返回的同步时间，缺失写 null。
- `coverage_note`：实际扫描范围及未覆盖说明；`limitations`：重要缺口字符串列表。未取得有效行情或新闻未核验时在这里说明，首屏显示。序列被降频、条数被截断或价格类型非默认时一并写在这里。已约定的合约类型、分钟 `last` 统一放在来源与口径。汇率缺失可在关联观察末尾简述。
- `takeaways`：少量 `{title, text}` 对象；重要事实在对应事件/行情明细中可溯源。`observations` 同结构，按“本期变化 → 国内关联品种与参考意义 → 必要限制”写具体短段，遵循 editorial.md；不放底层数据排障或通用基本面研究清单。
- `markets`：按唯一外盘标的去重的列表。每项提供 `name, exchange, symbol, basis, category, unit, domestic`（字符串数组）、`base, last`（数字或 null）、`base_time, last_time`（ISO 时间或 null）、`comparable`（布尔）、`note`、`source`。source 为实际来源及底稿定位，不放 Token；`basis` 写实际合约类型和原始价格口径，如“LME 三个月连续 · 原始分钟 last”，不能统一简写主力连续。`base/last` 及其时刻来自已核实原始统计或原始记录，禁止填聚合价／桶标签。若另有图表序列，聚合类型、频度和截断情况在 method_notes 单独说明。端点、窗口、价格与单位满足比较要求即可设 comparable=true；foreign 无需另附底层合约、换月明细或复权证明。symbol 未返回时明确写“未提供”，不得编造；不可比原因写入 note。`pre_window_anchor` 下晚于起点的基准不能进入排名；`in_window` 下允许窗口内首末记录，但需披露各标的实际覆盖，不冒充完整假期累计变化。`comparable=false` 的项在两种模式下均不进入排名；可将有效的原始统计涨跌及排除理由写入 note。
- `events`：无已核实事件时传空列表，渲染器隐藏事件章节、连续编号其余章节，行情存在时加“行情版”标签并披露资讯未纳入；不显示资讯检索截止，也不表示区间内无事件。有事件时每项包含 `title, happened_at, published_at, fact, interpretation, watch, timing_note, sources`。前两者是供展示的时间字符串，必须标明日期、时区；历史资料不确定时如实写明。`sources` 为 `{label, url}` 列表，仅 http/https 链接。`timing_note` 必须说明相对相关行情时点的位置，尤其“行情截止后新增事件”。
- `method_notes`：来源与方法说明字符串数组，写明实际采用的时区、价格口径、基准边界、原币种/汇率处理及数据来源。foreign 按已约定的北京时间、实际合约类型（主力连续 / LME 三个月连续 / 新马连一、连二、连三）、原始统计端点与价格类型（分钟 `last`）说明；若另取序列，单独说明实际频度、聚合类型及降频／截断情况，不将其写成统计计算依据；其他来源按其实际口径说明。详细排障记录留在底稿。
- `risk_level`：normal/enhanced；`risk_disclaimer`：渲染器按固定文本写入配套底稿，方便下轮承接。脚本输出 `report.evidence.json`，只存研究数据，不存连接凭证。

## 视觉与复核

统一米白、深墨色、金色强调；国内习惯红涨绿跌，同时使用正负号和文字，不仅靠颜色。首屏是要点和实际行情覆盖，避免巨型封面。图表只展示满足端点与数据质量要求的项，连续合约的原始端点可参与排名，按涨跌幅排序，零轴清楚；完整主表和无法计算项可展开。来源和时点不能藏到只靠悬停才能读取。

交付前核对图文数值一致、引用可点击、无演示残留；检查宽屏和约 390px 窄屏，无页面横向溢出，表格允许内部横向滚动。打印时所有折叠明细展开、来源与风险提示保留。可用浏览器或渲染工具检查；若工具不可用，说明尚未完成视觉验证，不能声称已检查。

默认交付 HTML 链接与主要覆盖说明。底稿随文件保留便于复现，更新时保留 endpoint_mode 和基准口径，但不在面向客户的首屏介绍内部 schema、MCP 工具名、调用次数或测试状态。不得在未经用户要求时部署网站或主动发送给第三方。
