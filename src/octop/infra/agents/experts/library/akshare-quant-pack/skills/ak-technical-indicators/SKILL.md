---
name: ak-technical-indicators
description: '用纯 pandas/numpy 计算技术分析指标：MA/EMA/MACD/RSI/BOLL布林带/KDJ/ATR/动量ROC/年化波动率， 含统一口径规范（前复权、热身期、无前视偏差）与内置计算脚本。凡用户提到算指标、均线、金叉死叉、
  MACD、RSI 超买超卖、布林带、KDJ、ATR 波动率、技术信号、动量打分，或需要在行情数据上 补充指标列——即使没有明说"算指标"——都必须使用本技能，禁止凭记忆手写公式导致口径漂移。

  '
metadata:
  octop:
    emoji: 📈
    label:
      zh: 技术指标
      en: Technical Indicators
    summary:
      zh: 统一口径计算 MA/MACD/RSI/BOLL/KDJ/ATR 等指标。
      en: Compute MA/MACD/RSI/BOLL/KDJ/ATR with unified conventions.
    requires:
      bins:
      - python3
---

# ak-technical-indicators — 技术指标计算引擎

## 1. 何时使用

行情数据到手后的下一步。典型触发：给 K 线加指标列、生成均线金叉死叉信号、计算 ATR 做
止损距离、多因子打分里的动量/波动率因子、判断超买超卖状态。
使用本技能的原因很朴素：**指标公式的参数与实现细节（EMA 种子、Wilder 平滑、min_periods）
最容易"各写各的"**，本技能把口径锁死，团队所有人算出来的 MACD 是同一个 MACD。

## 2. 输入前提

- 输入必须是**前复权（qfq）日线** OHLCV 数据（用 `ak-market-data` 技能获取）。
- 标准列名：`date, open, high, low, close, volume`（脚本会自动识别并映射常见中文列名）。
- 数据升序、无重复日期；停牌缺口是否填充需在交付说明中声明。

## 3. 指标目录与口径规范（锁死，不得擅自改动）

| 指标 | 参数 | 实现口径 |
|---|---|---|
| SMA 简单均线 | 默认 5/10/20/60 | `close.rolling(n).mean()`；窗口不满输出 NaN（min_periods=n） |
| EMA 指数均线 | 12/26 或指定 | `pandas ewm(span=n, adjust=False)`，种子用首个收盘价 |
| MACD | 12, 26, 9 | DIF=EMA12−EMA26；DEA=EMA9(DIF)；MACD柱=2×(DIF−DEA)（A股软件惯例×2，注释注明） |
| RSI | 14 | **Wilder 平滑**（`ewm(alpha=1/n, adjust=False)`），与主流行情软件一致；不用简单均值版 |
| BOLL 布林带 | 20, 2 | 中轨=SMA20；上下轨=中轨 ±2×总体标准差（ddof=0，与通达信一致） |
| KDJ | 9, 3, 3 | RSV=(C−L9)/(H9−L9)×100；K=SMA3(RSV) 即 ewm(alpha=1/3)；D=SMA3(K)；J=3K−2D |
| ATR | 14 | TR=max(高−低, |高−昨收|, |低−昨收|)；ATR=Wilder 平滑 |
| ROC 动量 | 12 | close/close.shift(n)−1 |
| 波动率 | 20 | 日收益率 std×√252，年化，滚动窗口 |

**三条铁律：**
1. **无前视：** 一切指标只用 T 日及以前数据；信号生效一律 T+1（回测与实盘同一口径）。
2. **热身期透明：** 前置 NaN 是正常的（60 日线前 59 行必为 NaN），禁止 dropna 后悄悄混入下游，热身期长度要在交付时声明。
3. **复权一致：** 指标只在 qfq 序列上算；换股/换合约必须重算，禁止跨序列复用指标缓存。

## 4. 内置脚本：indicators.py

一条命令把指标批量补到 CSV 上（纯 pandas/numpy，无额外依赖，可离线运行）：

```bash
# 全量指标
python3 "skills/ak-technical-indicators/scripts/indicators.py" --input ~/quant-data/raw/000001_daily.csv \
    --output ~/quant-data/proc/000001_with_ind.csv

# 只算部分 + 自定义均线组
python3 "skills/ak-technical-indicators/scripts/indicators.py" --input kline.csv --output out.csv \
    --indicators ma,ema,macd,rsi,boll,kdj,atr,roc,vol --ma-periods 5,10,20,60,120

# 指定指标参数
python3 "skills/ak-technical-indicators/scripts/indicators.py" --input kline.csv --output out.csv \
    --indicators rsi --rsi-period 6
```

输出：原表 + 指标列（命名如 `ma_20, macd_dif, macd_dea, macd_hist, rsi_14, boll_up,
kdj_k, atr_14, roc_12, vol_20`），并在 stdout 打印每列热身期与末行快照。

## 5. 常见坑（每一坑都真实翻过车）

1. **EMA 种子差异：** 不同软件 EMA 初值不同，长序列下收敛一致，但**短样本（<3×周期）时两家算出来会不同**——样本不足 3 倍周期时明确提示用户结论不稳。
2. **RSI 两种流派：** 简单均值版 vs Wilder 版数值不同，跨软件对比时先确认口径；本团队统一 Wilder。
3. **KDJ 的 SMA 是"中国式 SMA"：** `Y=(X×1+Y'×2)/3`，本质是 `ewm(alpha=1/3)`，直接用 pandas 的 `rolling` 或 `sma` 会错。
4. **布林带标准差口径：** `ddof=0`（总体）vs `ddof=1`（样本）有细微差异；本团队锁 0 与通达信一致。
5. **分红除权日跳空：** 不复权数据上算指标会出现假跳空假金叉；指标计算前先确认 qfq。
6. **信号 vs 指标混淆：** 指标列（如 MACD 柱）不等于交易信号（如"柱由负转正且 >0.05"）；信号定义由 Signal 岗在研究单中显式写出，本技能只管指标列。

## 6. 交付标准

- 输出 CSV 附"指标身份证"：指标清单+参数、热身期行数、输入数据的复权口径声明。
- 下游（回测/选股）引用指标时，必须同时引用该身份证，保证口径可追溯。
