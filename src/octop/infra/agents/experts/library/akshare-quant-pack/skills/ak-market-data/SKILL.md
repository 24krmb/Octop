---
name: ak-market-data
description: '基于 AKShare 获取 A股 / 指数 / 行业与概念板块 / 国内期货 / 期权的实时与历史行情数据， 输出标准化的英文列名 CSV。凡用户提到任何股票代码、K线、日线/周线/月线/分钟线、历史数据、
  实时行情、涨跌幅、成交量、复权、数据下载、行情快照、期货合约、主力连续、期权报价， 或者任何分析的第一步需要行情数据时——即使用户没有明说"取数据"——都必须先使用本技能。 这是 AKShare 量化团队所有数据获取的唯一入口。

  '
metadata:
  octop:
    emoji: 📡
    label:
      zh: 行情获取
      en: Market Data
    summary:
      zh: 基于 AKShare 获取 A股、指数、板块、期货与期权行情。
      en: Fetch A-share, index, sector, futures, and options quotes via AKShare.
    requires:
      bins:
      - python3
---

# ak-market-data — 行情数据获取技能

## 1. 何时使用

任何需要市场数据的时刻。典型触发：查某只股票的历史走势、下载多只股票日线做研究、
看期货主力合约行情、取指数数据做基准、板块轮动监控、期权合约价格查询。
本技能是流水线第一站：上游数据不对，下游全白算，所以取数永远自己来做、绝不猜测数据。

## 2. 环境自检（每次会话首次取数前执行一次）

```bash
python3 -c "import akshare as ak, pandas as pd; print('akshare', ak.__version__)"
```

- 未安装：`pip install akshare pandas --upgrade`（建议锁定版本，见第 6 节）。
- **AKShare 接口随版本演进，接口名与返回的中文列名都可能变化。** 调用任何接口后
  第一步永远是 `print(df.columns.tolist())` 确认字段，再写下游逻辑。

## 3. 核心工作流

1. **解析需求：** 标的（代码/合约）、区间、频率、复权口径、字段。口径不明先问用户。
2. **选接口：** 按第 4 节速查表选择；东财系（`*_em`）数据全但频率限制严，新浪系（`*_sina`）
   稳定但字段少，互为备份。
3. **取数：** 优先用本技能脚本 `scripts/fetch_ohlcv.py`（自带重试、列名映射、质检输出）。
4. **质检：** shape / 列名 / 缺失值 / 异常值（如涨跌幅绝对值 >44% 疑似数据错误）/ 重复行。
5. **落盘与留痕：** 存 `~/quant-data/raw/`，打印"数据身份证"（接口、时间戳、参数、复权）。

## 4. 接口速查表

> 表中接口名以 akshare 1.1x 为基准。若调用报错（AttributeError / KeyError），
> 用 `[i for i in dir(ak) if '关键词' in i]` 检索同族接口，并查官方文档 akshare.akfamily.xyz。

### A 股与指数

| 需求 | 接口 | 关键参数与说明 |
|---|---|---|
| A股全市场实时快照 | `ak.stock_zh_a_spot_em()` | 无参数；字段含 代码/名称/最新价/涨跌幅/换手率/市盈率-动态/市净率/总市值 等；一次请求，注意限频 |
| A股历史K线（东财） | `ak.stock_zh_a_hist(symbol, period, start_date, end_date, adjust)` | `period`: daily/weekly/monthly；`adjust`: `""`/`"qfq"`(前复权)/`"hfq"`；日期格式 `YYYYMMDD`；指标计算一律用 `qfq` |
| 分钟线 | `ak.stock_zh_a_hist_min_em(symbol, period, start_date, end_date, adjust)` | `period`: 1/5/15/30/60 分钟；历史分钟数据区间有限，超出需分批 |
| 指数日线（东财） | `ak.index_zh_a_hist(symbol, period, start_date, end_date)` | 如 `symbol="000300"` 沪深300、`"000001"` 上证（注意指数代码无交易所前缀） |
| 指数日线（新浪） | `ak.stock_zh_index_daily_em(symbol="sh000001")` | 带交易所前缀 `sh/sz`；作为东财指数接口的备份 |
| A股代码清单 | `ak.stock_info_a_code_name()` | 返回全市场 代码+名称，用于代码校验与股票池构建 |
| 交易日历 | `ak.tool_trade_date_hist_sina()` | 全部交易日列表；多标的对齐与"今天是否交易日"判断都用它 |

### 板块（行业 / 概念）

| 需求 | 接口 | 说明 |
|---|---|---|
| 行业板块列表 | `ak.stock_board_industry_name_em()` | 板块名列表及涨跌快照 |
| 行业板块历史K线 | `ak.stock_board_industry_hist_em(symbol, start_date, end_date, period, adjust)` | `symbol` 用板块中文全称（如"小金属"） |
| 概念板块列表 | `ak.stock_board_concept_name_em()` | 数量多、更新快，注意限频 |

### 期货

| 需求 | 接口 | 说明 |
|---|---|---|
| 主力连续日线 | `ak.futures_main_sina(symbol, start_date, end_date)` | `symbol="RB0"` 螺纹主力；返回含 开盘价/最高价/最低价/收盘价/成交量/持仓量/动态结算价 |
| 具体合约日线 | `ak.futures_zh_daily_sina(symbol)` | 如 `symbol="RB2410"`；日期格式与字段与上不同，先看列名 |
| 主力连续清单 | `ak.futures_display_main_sina()` | 可查所有品种的主力连续代码（`xx0`），品种映射的第一入口 |
| 期货历史（东财） | `ak.futures_hist_em(symbol, period, start_date, end_date)` | `symbol` 用中文合约名如"螺纹钢2410"；作为新浪源备份 |

### 期权

| 需求 | 接口 | 说明 |
|---|---|---|
| 上交所期权合约日线 | `ak.option_sse_daily_sina(symbol)` | `symbol` 为合约代码（如 `10003662`）；需先有合约清单 |
| 期权接口族检索 | `[i for i in dir(ak) if i.startswith('option_')]` | 期权类接口多而杂（T型报价、 Greeks、到期日等），**优先用官方文档"期权"章节核对当前版本可用的接口与参数**，再调用 |

## 5. 内置脚本：fetch_ohlcv.py

一键完成"取数 → 中文列名映射英文 → 重试 → 质检 → 落盘 + 数据身份证"：

```bash
# A股个股日线（前复权）
python3 "skills/ak-market-data/scripts/fetch_ohlcv.py" --kind stock --symbol 000001 \
    --start 20230101 --end 20251231 --adjust qfq --out ~/quant-data/raw/000001_daily.csv

# 指数日线
python3 "skills/ak-market-data/scripts/fetch_ohlcv.py" --kind index --symbol 000300 \
    --start 20230101 --end 20251231 --out ~/quant-data/raw/hs300_daily.csv

# 期货主力连续
python3 "skills/ak-market-data/scripts/fetch_ohlcv.py" --kind futures_main --symbol RB0 \
    --start 20230101 --end 20251231 --out ~/quant-data/raw/rb_main.csv

# 期货具体合约
python3 "skills/ak-market-data/scripts/fetch_ohlcv.py" --kind futures_contract --symbol RB2410 \
    --out ~/quant-data/raw/rb2410.csv
```

脚本行为：失败自动重试 3 次（间隔递增）；输出英文标准列名
（date/open/high/low/close/volume/amount/…）；末尾打印缺失值统计与数据身份证。
脚本路径均相对于工作区根目录（`skills/ak-market-data/scripts/`），执行前确认当前目录为工作区根，或改用脚本的完整相对路径。

## 6. 防御性规范与常见坑

1. **先看列名再写逻辑。** 中文列名随版本变化，硬编码列名是最大事故来源。
2. **复权口径统一。** 技术指标/收益率计算用 `qfq`；财务与市值类用不复权；报告中必须注明口径。
3. **限频与礼貌。** 东财系接口批量调用时每次间隔 ≥1 秒并加重试；被限频（返回空或报错）就退避等待，不要连环轰炸。
4. **停牌与缺失。** 日线缺行 = 停牌或非交易日；多标的合并用交易日历对齐，NaN 处理方式显式声明，禁止静默填充。
5. **北向资金提醒：** 沪深港通北向实时买卖数据自 2024 年 8 月起停止逐日披露，实时北向"净买入"已不可得；历史与汇总口径请用 `ak-fund-flow` 技能并注明口径。
6. **版本锁定。** 生产研究环境锁定 akshare 版本（如 `pip install akshare==1.16.98`），升级前先跑本技能自检，防止接口静默变更毁掉可复现性。
7. **不编数。** 任何接口失败都如实报告失败与已尝试的替代路径；缺数可以补取，编数不可原谅。

## 7. 交付标准

- CSV 文件：UTF-8、英文标准列名、date 列为 `YYYY-MM-DD` 字符串且升序。
- 数据身份证随文件输出（接口名、抓取时间戳、参数、复权、行数）。
- 任何降级（换源、缺区间、字段缺失）必须在交付说明中逐条列出。
