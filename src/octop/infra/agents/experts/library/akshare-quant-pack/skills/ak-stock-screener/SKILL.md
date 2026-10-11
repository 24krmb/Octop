---
name: ak-stock-screener
description: '多因子选股筛选技能：基于 AKShare 数据做股票池构建、硬条件初筛与技术面+基本面多因子 打分（动量/趋势/流动性/估值/质量），内置单次请求的快照筛选脚本与逐票深加工流程。
  凡用户提到选股、筛选、股票池、打分、多因子、低估值、高动量、找票、什么股票符合条件、 帮我选出——即使没有明说"选股"——都必须使用本技能。禁止在输出筛选结果时不声明 打分口径与数据时点。

  '
metadata:
  octop:
    emoji: 🔍
    label:
      zh: 多因子选股
      en: Stock Screener
    summary:
      zh: 硬条件初筛加动量/估值/质量多因子打分。
      en: Screen stocks via hard filters and multi-factor scoring.
    requires:
      bins:
      - python3
---

# ak-stock-screener — 多因子选股技能

## 1. 何时使用

一切"从全市场里挑票"的任务：低估值+高动量组合构建、超跌反弹候选池、行业轮动内选强票、
基本面硬条件过滤（市值/估值/流动性）后的技术面打分。
选股是"漏斗+打分"两段式工作：**先硬条件砍掉 90%，再对剩余 10% 做因子打分排序**。
反过来先打分再过滤是常见的算力浪费和口径混乱来源。

## 2. 数据地基（按需取用，全部来自 `ak-market-data` 技能）

| 层 | 接口 | 用途 |
|---|---|---|
| 全市场快照 | `ak.stock_zh_a_spot_em()` | 一次请求拿全市场 最新价/涨跌幅/换手率/市盈率-动态/市净率/总市值/60日涨跌幅/年初至今涨跌幅 等，初筛与快照因子的主料 |
| 代码清单 | `ak.stock_info_a_code_name()` | 剔除北交所/退市整理等非目标范围 |
| 估值历史 | `ak.stock_a_indicator_lg(symbol)` | 乐咕口径 PE/PB/PS/股息率历史；逐票深加工用 |
| 历史K线 | `ak.stock_zh_a_hist(..., adjust="qfq")` | 技术面因子（动量/趋势/波动）的逐票原料 |
| 财务指标 | `ak.stock_financial_analysis_indicator(symbol, start_year)` | 质量/成长因子（ROE、营收增速等），注意**公告延迟** |
| 交易日历 | `ak.tool_trade_date_hist_sina()` | 区间计算与停牌对齐 |

**快照字段注意：** `stock_zh_a_spot_em` 的列名随版本微调（如"市盈率-动态"），取数后先
`print(df.columns.tolist())`；内置脚本已做字段自动探测，但新增字段需人工确认含义。

## 3. 因子库（默认口径，可扩展）

| 因子族 | 因子 | 计算 | 经济逻辑 |
|---|---|---|---|
| 动量 | 60日收益 | 快照 60日涨跌幅 或 hist 收盘 60 日收益 | 趋势惯性（行为金融：反应不足） |
| 动量 | 20日动量 | hist 收盘 20 日收益 | 短期动量，换手成本高需谨慎 |
| 趋势 | 均线结构 | close > MA20 > MA60 记 1 分 | 多头排列强度 |
| 趋势 | 距 52 周高点 | close / 52周最高 − 1 | 接近新高的相对强度 |
| 流动性 | 20日均成交额 | hist amount 均值 | 可交易性门槛，兼作流动性风险控制 |
| 波动 | 60日年化波动 | 日收益 std×√252 | 低波动因子（风险调整） |
| 估值 | PE 分位 | `stock_a_indicator_lg` 历史分位 | 自历史比较，防跨行业 PE 直接比较 |
| 估值 | PB/股息率 | 快照或乐咕 | 防御性因子 |
| 质量 | ROE/增速 | 财务指标接口 | 基本面支撑；必须按公告日对齐防前视 |

**打分规范：** 因子值先做**截面去极值（±3 MAD）→ z-score 标准化 → 按权重加权**；
方向以研究单为准（如"低波动"取负号）。禁止跳过去极值直接打分——单只异常票会污染全池排名。

## 4. 内置脚本：screener_template.py

**单次请求完成初筛+快照打分**（不逐票拉历史，速度快、对接口友好）：

```bash
python3 "skills/ak-stock-screener/scripts/screener_template.py" \
    --min-amount 2 --max-pe 40 --min-pe 0 --min-mktcap 50 \
    --exclude-bj --exclude-st \
    --weights momentum60:0.4,turnover:0.2,pb:0.2,amplitude:0.2 \
    --top 30 --out ~/quant-data/proc/screener_result.csv
```

- `--min-amount`：最低成交额（亿元，流动性门槛）；`--min/max-mktcap`：市值区间（亿元）
- `--exclude-bj/--exclude-st`：剔除北交所与 ST（默认开）
- `--weights`：因子权重（可组合：momentum60/turnover/pb/pe/amplitude/mktcap）
- 输出：Top-N 表 + 全量打分明细 + 口径声明（数据时点、字段方向、缺失处理）

**升级路径：** 快照打分给出候选池后，对 Top-N 逐票调用 `stock_zh_a_hist`（qfq）+
`stock_a_indicator_lg` 做 §3 完整因子库打分，每票间隔 ≥1 秒；50 票以内可接受，
500 票以上建议派 Data 岗分批跑并落盘中间结果。

## 5. 方法论红线

1. **幸存者偏差：** 基于"今天还活着"的名单回测历史选股 = 作弊；研究型选股必须声明该局限。
2. **前视偏差：** 财务因子用公告日（`ann_date`）对齐，不用报告期；快照打分只声称"今日截面"，不做历史收益承诺。
3. **行业中性：** 跨行业直接比较估值/动量意义有限，正式研究需按申万一级行业分组打分或做行业中性化。
4. **样本外纪律：** 因子权重调整属于策略研究，必须走 Signal 岗研究单 + Echo 岗回测流程，禁止看着今天的热点随手改权重。
5. **免责：** 筛选结果=统计排序，不是买入清单；交付时附 AGENTS.md 固定免责声明。

## 6. 交付标准

- 结果表字段：代码、名称、打分、各因子原始值与 z-score、硬条件命中标记、数据时点。
- 口径声明随表输出：因子定义、权重、去极值方法、缺失票处理、接口名与抓取时间。
- Top-N 结果同时落盘 CSV 与报告表格两种形态（后者供 Quill 岗直接引用）。
