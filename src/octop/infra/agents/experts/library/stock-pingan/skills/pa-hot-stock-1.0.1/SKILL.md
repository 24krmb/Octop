---
name: pa-hot-stock
description: 查询平安证券热股榜单数据，覆盖 4 类榜单——热搜榜（用户都在搜的标的）、加自选榜（用户都在加自选的标的）、浏览榜（用户都在看的标的）、飙升榜（关注度飙升最快的标的），支持 A股/ETF/板块概念/港股/可转债 5 个类别。当用户询问"今天什么股票最热"、"大家都在搜什么"、"大家都在加什么自选"、"大家都在看什么"、"哪些票关注度飙升"、"ETF/港股/可转债热度榜"、"热股风向标"等与市场热度、人气榜单相关的问题时，使用此 skill 获取实时数据。用户提到"热股""热搜""人气榜""风向标""加自选""飙升"等字眼时，也应主动触发。
---

# 热股风向标 Skill

## 这个 Skill 做什么

查询平安证券热股榜单数据，反映平安证券用户群体的实时关注方向，覆盖 4 类榜单：

| 榜单 | 含义 |
|---|---|
| 热搜榜 | 平安证券用户都在**搜索**的标的榜单 |
| 加自选榜 | 平安证券用户都在**加自选**的标的榜单 |
| 浏览榜 | 平安证券用户都在**看**的标的榜单 |
| 飙升榜 | **关注度飙升**最快的标的榜单 |

前三个榜单代表用户行为的不同深度：浏览（看一眼）→ 热搜（主动找）→ 加自选（持续跟踪）；飙升榜则反映关注度的变化速度而非绝对量。回答时可以据此区分说明。

所有请求都通过 `scripts/get_data.py` 这一个脚本发出，用 `--module_code` 区分榜单类型。

#### 任何时候都应该用这个 skill 实际查询，不要依赖训练知识回答榜单排名、热度、涨跌幅等具体内容。

## 环境准备

- 检查是否已经设置环境变量 `PINGAN_SKILL_APIKEY`（用于鉴权用的 API Key），如未设置，提示用户登录平安证券skill开放平台获取 https://stock.pingan.com/huodong/aiskill/skillPage/index.html#/
- 依赖 Python 库 `requests`。

## 基本调用格式

```bash
python scripts/get_data.py --module_code <榜单类型> --type_code <二级类别> [--time_range N] [--size N]
```

## 参数一览

| 参数 | 类型 | 必填 | 说明 | 限制 |
|---|---|---|---|---|
| `--module_code` | string | Y | 榜单类型 | 取值见下表 |
| `--type_code` | string | Y | 二级 tab 类型 | 取值见下表 |
| `--time_range` | int | N | 时间区间 | `1`=1h、`2`=24h；**默认 2（24h）** |
| `--size` | int | N | 返回条数 | **默认 10**，最多 100 |

**module_code 榜单类型**

| 取值 | 榜单 | 含义 |
|---|---|---|
| `hot_stock` | 热搜榜 | 平安证券用户都在搜索的标的榜单 |
| `hot_select` | 加自选榜 | 平安证券用户都在加自选的标的榜单 |
| `hot_watch` | 浏览榜 | 平安证券用户都在看的标的榜单 |
| `hot_surge` | 飙升榜 | 关注度飙升最快的标的榜单 |

**type_code 二级类别**

| 取值 | 含义 |
|---|---|
| `aStock` | A股 |
| `etf` | ETF |
| `block` | 板块概念 |
| `hkStock` | 港股 |
| `bond` | 可转债 |

四类榜单支持的参数组合完全一致：五个二级类别都支持，时间区间都支持 1h / 24h。

> `size` 超出 1～100 会被直接拦截，不会发起网络请求。

## 返回字段

| 字段 | 说明 |
|---|---|
| `updateTime` | 榜单更新日期（yyyy-mm-dd） |
| `list[]` | 榜单条目，按热度顺序排列 |

`list[]` 内每个条目：

| 字段 | 说明 |
|---|---|
| `marketType` | 市场（如 `SH`、`SZ`、`HK`） |
| `stockCode` | 代码 |
| `name` | 名称 |
| `chg` | 涨跌幅，**小数形式的字符串**（如 `-0.0391` 表示 -3.91%），展示时需自行乘 100 |
| `updateTime` | 该条目的更新日期（yyyy-mm-dd） |

输出示例：

```json
{
  "list": [
    {
      "chg": "-0.0391",
      "marketType": "SH",
      "name": "宇树科技-W",
      "stockCode": "688836",
      "updateTime": "2026-09-02"
    }
  ],
  "updateTime": "2026-09-02"
}
```

## 调用示例

```bash
# A股 24h 热搜榜前 10（等价于 --time_range 2 --size 10）
python scripts/get_data.py --module_code hot_stock --type_code aStock

# A股近 1 小时加自选榜前 20
python scripts/get_data.py --module_code hot_select --type_code aStock --time_range 1 --size 20

# 板块概念 24h 飙升榜
python scripts/get_data.py --module_code hot_surge --type_code block

# 港股 24h 浏览榜前 30
python scripts/get_data.py --module_code hot_watch --type_code hkStock --size 30

# ETF 24h 热搜榜
python scripts/get_data.py --module_code hot_stock --type_code etf

# 可转债 24h 热搜榜
python scripts/get_data.py --module_code hot_stock --type_code bond
```

---

## 使用提示

- 用户没有指明时间区间时不用传 `--time_range`，脚本默认按 24h 发；说"刚刚/现在/这一小时"时显式传 `--time_range 1`。
- 用户没有指明品种时，默认查 A股（`--type_code aStock`）。
- 用户没有指明条数时不用传 `--size`，默认 10 条；要"前 20""前 50"时再显式传。
- `chg` 是小数形式（`-0.0391` = -3.91%），**换算后再展示**，不要直接把 `-0.0391` 当成 -0.04% 说。
- 榜单是热度/关注度排序，不是涨幅排序，回答时不要把榜单名次说成涨幅名次。
- 飙升榜衡量的是关注度的**增速**，上榜标的绝对热度未必高；热搜/浏览/加自选榜衡量的是**绝对量**。两者含义不同，不要混着说。
- 榜单反映的是平安证券用户群体的行为，不代表全市场，也不构成投资建议。
- 返回结果里的 `updateTime` 是榜单数据的更新日期，回答时可以带上，便于用户判断时效性。
- 需要标的的实时价格、资金流向、K线等行情数据时，配合行情查询 skill 使用。

参数和取值范围可以直接看帮助信息：

```bash
python scripts/get_data.py -h
```
