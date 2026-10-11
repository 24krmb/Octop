---
name: ak-quant-report
description: '量化报告与绩效计算技能：用统一口径计算绩效指标（年化收益/波动/夏普/索提诺/最大回撤/ 卡玛/胜率/盈亏比/月度收益表），产出标准化净值曲线与图表（中文字体、口径脚注齐全），
  并按团队五段式报告模板成文。凡用户提到报告、总结、复盘、绩效、业绩、收益统计、 净值曲线画图、夏普是多少、回撤多少、绩效归因——即使没有明说"出报告"—— 都必须使用本技能。禁止手算绩效指标（口径漂移），禁止交付无免责声明的报告。

  '
metadata:
  octop:
    emoji: 📝
    label:
      zh: 量化报告
      en: Quant Report
    summary:
      zh: 绩效指标计算与五段式复盘报告。
      en: Performance metrics and structured review reports.
    requires:
      bins:
      - python3
---

# ak-quant-report — 量化报告与绩效计算技能

## 1. 何时使用

流水线终点站：回测跑完要出绩效、持仓一段时间要复盘、用户要"给我一份总结"、
因子要定期监控。本技能保证两件事：**所有人算出的夏普是同一个夏普**；
**所有报告长得像同一套研究所出品**。

## 2. 绩效指标统一口径（performance.py 内置实现，禁止另算）

| 指标 | 口径 | 备注 |
|---|---|---|
| 年化收益 | 几何年化：NAV^(1/年数)−1 | 年数按 244 交易日折算 |
| 年化波动 | 日收益 std(ddof=0)×√244 | |
| 夏普比率 | (年化收益−无风险利率)/年化波动 | 无风险默认 2%，可用 `--rf` 调整 |
| 索提诺 | 年化超额 / 下行波动 | 下行波动只计负收益 |
| 最大回撤 | 净值/滚动最高−1 的最小值 | 输出起止日期与修复日期 |
| 卡玛比率 | 年化收益 / \|最大回撤\| | |
| 胜率/盈亏比 | 仅当提供交易明细时计算 | 按平仓配对 |
| 月度收益表 | 净值月末重采样 | 输出 12×N 热力图可读表格 |

## 3. 内置脚本：performance.py

```bash
# 净值曲线绩效（equity.csv 至少含 date 与 nav 两列；可带 benchmark_nav）
python3 "skills/ak-quant-report/scripts/performance.py" --equity ~/quant-data/backtests/demo/equity.csv \
    --rf 0.02 --out-dir ~/quant-data/reports/demo_perf

# 带交易明细时自动算胜率/盈亏比
python3 "skills/ak-quant-report/scripts/performance.py" --equity equity.csv \
    --trades trades.csv --out-dir ./perf_out
```

输出（--out-dir）：`performance.json`（机器可读全指标）、`performance.txt`（报告可直接
引用的表格）、`nav_curve.png`（策略 vs 基准净值+回撤阴影，中文字体自动配置）。

## 4. 图表规范（每张图五要素，缺一即打回）

1. **标题**：含标的与策略名；2. **轴单位**：价格(元)/收益率(%)；3. **数据区间**：起止日期；
4. **口径脚注**：复权方式、成本假设、数据源；5. **中文字体**：matplotlib 需显式配置
（`Noto Sans SC` / `SimHei`，脚本已内置探测），否则中文变方块。
配图基线：净值曲线（含基准对比）、回撤曲线、月度收益热力表；其他图按需增加。

## 5. 报告模板（五段式，与 Quill 岗输出契约一致）

```markdown
# <报告标题>（YYYY-MM-DD）
## 一、核心结论          ≤3条，每条一句话，数字带口径与区间
## 二、关键数据表        绩效总表（来自 performance.txt）、Top持仓/Top信号
## 三、方法与数据口径    数据源接口、复权、成本假设、样本区间、指标定义
## 四、风险提示与风控意见 Sentinel 结论原样呈现；触发红线的必须显著标注
## 五、数据来源与免责声明 固定免责文案（AGENTS.md §5）+ 生成时间戳
```

**写作纪律：** 结论先行、表格优先、术语首现必解释、不新增团队未得出的观点、
难看的数据（大回撤/低胜率/否决意见）必须原样呈现——报告的公信力来自不回避。

## 6. 交付标准

- `performance.json` + `performance.txt` + 图表 PNG 一并落盘 `~/quant-data/reports/`。
- 报告正文（md）与图表同目录存放，文件名含日期与主题。
- 任何"绩效超常"的数字（年化>50%且回撤<10%）在正文显著位置提示"先查实现错误"
  （呼应 `ak-backtest` §5 红灯清单）。
