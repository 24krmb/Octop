---
name: discuz-api-publisher
description: 必须用于通过 Discuz! X5 RESTful API 执行论坛自动化操作：自动发帖（发布新主题）、回帖（回复主题）、发布门户文章，以及读帖/看版块。配置已预置于技能目录 config.json（站点 24krmb.com，凭据与接口清单已登记）。当用户要求"发帖""回帖""发布文章""推送到论坛""看论坛帖子"等涉及 Discuz 论坛的任务时直接使用，无需再向用户询问配置。Must use for posting, replying, publishing articles, and reading on the pre-configured Discuz! X5 site (24krmb.com) via RESTful API.
metadata:
  octop:
    emoji: "📢"
    label:
      zh: "Discuz 论坛发布"
      en: "Discuz Publisher"
    summary:
      zh: "调用已配置的 24krmb.com Discuz! RESTful API：发帖、回帖、发文章、读帖。"
      en: "Call the configured Discuz! RESTful API on 24krmb.com: post, reply, publish, read."
---

# Discuz! 论坛自动发布（24krmb.com · 已配置）

站点配置**已预置**在技能目录 `config.json`（site/appid/secret/endpoints 全量登记），**直接发起，不要向用户询问任何配置**。

## 〇、启动检查（每次会话首次调用前执行一次）

```python
import json, urllib.request, urllib.parse, hashlib, base64, time, uuid, os

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))  # 或从 {{OCTOP_BUILTIN_SKILLS}}/discuz-api-publisher 拼接
cfg = json.load(open(f"{{OCTOP_BUILTIN_SKILLS}}/discuz-api-publisher/config.json"))
site, appid, secret = cfg["site"], cfg["app"]["appid"], cfg["app"]["secret"]
UA = "24K-Claw-Octop/1.0"   # ⚠️ 必须用程序化 UA；伪装浏览器 UA 会被站点 WAF 判 bot 直接 403
```

**config 缺项处理**：若 `appid/secret` 为空 → 停止并告知站长「需要在 Discuz 后台创建应用并填入 config.json」；若目标操作的 endpoint 缺失 → 告知需导入对应接口 XML（见〇之附）。**仅此两种停止场景，其余一律直接执行。**

## 一、签名与请求（每次调用）

```python
def make_headers(token=None):
    nonce, t = str(uuid.uuid4()).replace("-", "")[:20], str(int(time.time()))
    h = {"appid": appid, "nonce": nonce, "t": t,
         "sign": base64.b64encode(hashlib.sha256((nonce + t + secret).encode()).hexdigest().encode()).decode(),
         "User-Agent": UA}
    if token: h["token"] = token
    return h

def call(path, payload=None, token=None):
    url = f"{site}/api/restful/?/{path}"
    data = urllib.parse.urlencode({"_REQUEST": json.dumps(payload or {}, ensure_ascii=False)}).encode()
    req = urllib.request.Request(url, data=data, headers=make_headers(token))
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())
```

签名 = `base64(sha256(nonce + t + secret))`（顺序固定，**不是 HMAC**），300 秒 TTL；nonce 每次必须新 UUID。

## 二、登录与 Token（发帖/回帖前必须登录）

**账号发帖流程**（实测：免登录发帖=游客 uid:0；登录后 uid=6440"复盘侠"）：

```python
tok = call("token")["token"]
login = call("member/login",
    {"GET": {"mod": "logging", "action": "login", "loginsubmit": "yes"},
     "POST": {"fastloginfield": "username", "username": cfg["credentials"]["forum_username"],
              "password": cfg["credentials"]["forum_password"], "cookietime": "2592000"}},
    token=tok)
# 成功标志：login["data"]["msg"]["message"] == "location_login_succeed"
# 用同一 tok 调 newThread/reply → user.uid = 账号 uid
```

**规则**：发帖/回帖前必须 login；token 重取后**必须重新 login**；login 失败（密码错/需验证码）如实报告，禁止重试爆破。

### 二之附、Token（只读接口调用前必须）

```python
tok = call("token")["token"]     # {"ret":0,"token":"…","expires_in":<过期时间戳>}
```

- `expires_in` 为过期时间戳；可缓存进 workspace `.discuz_token.json` 复用，过期重取
- 业务请求把 token 放 Header `token`

## 三、已登记接口（endpoints）与当前可用性

**⚠️ 发帖实测成功的正确姿势（2026-10-12 验证）**：
- path = `newthread`（官方包），**POST 三参数：fid / subject / message**（全在 POST，无 GET、无 topicsubmit）
- **成功响应 = HTTP 301 跳转**（Discuz 发帖成功后转主题页）——**Body 里才有 JSON**：`{"ret":0,"data":{"msg":{"message":"post_newthread_succeed","url_forward":"thread-<tid>-1-1.html"},"tid":"4818","pid":"…"}}`
- 客户端必须能读 301 的 Body（urllib 用 NoRedirect handler / curl 不加 -L 直接读）；HTTP 200 + HTML = 表单页（未提交）
- 免登录调用 = 游客身份（uid:0）；发帖必须先 login（见二）

| 操作 | path | 状态 |
|---|---|---|
| 版块列表 | `index/forumlist` | ⚠️ 需站点导入官方接口包 |
| 版块帖子列表 | `forumdisplay` | ⚠️ 同上 |
| 看帖 | `viewthread` | ⚠️ 同上 |
| 登录信息 | `member/loginInfo` | ✅ 可用 |
| 账号登录 | `member/login` | ✅ 可用 |
| **发帖** | `forum/newThread` | ⚠️ 需导入 `discuz_newthread_reply.xml`（本技能附带） |
| **回帖** | `forum/reply` | ⚠️ 同上 |
| **门户文章** | `portal/publish` | ⚠️ 同上 |

调用返回 `ret:-109, msg:"getApiParam: api is invalid"` = 该接口在站点**未导入或未授权**——不是代码问题，转告站长完成〇之附的两步。

### fid 解析规则（发帖目标版块怎么定）

1. 用户明确报数字（"发到 126"）→ 直接用该 fid
2. 用户报版块**名称**（"发到各抒己见/实战案例"）→ 调 `index/forumlist`（读 data.forumlist 数组，含 subforums 递归）按 name 匹配出 fid
3. 用户未指定版块 → 用 `config.default_fid`（当前 = 159「各抒己见」），**并在预览时告知用户将发到此版块**

全站版块映射（2026-10-12 实测快照，forumlist 可随时刷新）：
138 交易(组) | 89 实战技术 | 126 实战案例 | 196 宏观能力 | 190 AI+ | 161 Ai+通达信 | 156 Ai+金融 | 132 Ai+运用 | 88 观点 | 140 赛道/研报 | **159 各抒己见(默认)** | 191 社区相关 | 143 藏金阁 | 104 资源下载 | 182 程序量化 | 170 入市学习

### 〇之附：站点侧开通步骤（站长在 Discuz 后台操作，一次性）（站长在 Discuz 后台操作，一次性）

```
1. 导入接口 XML：管理中心 → 站长 → RESTful 接口 → 导入接口
   a) 官方包 discuz_restful_official_trial.xml（读类+账号）
   b) 本技能附带 discuz_newthread_reply.xml（发帖/回帖/文章）
2. 分配权限：站长 → RESTful 接口 → 应用管理 → 编辑应用(19665625) → 勾选上述接口
3. 确认服务器 Redis 已配置（RESTful 硬依赖，未配置报 -110）
```

## 四、发帖/回帖/文章的执行流程（每次都遵循）

```
1. 读 config endpoints → 操作未登记或站点未导入（-109）→ 按〇之附提示，不猜测 path
2. Token 就绪（缓存复用/重取）
3. 填充参数：fid/tid/subject/message 等来自用户输入；缺失时询问，禁止猜测版块
4. 【红线】发帖/回帖前必须向用户预览（标题+正文+目标），明确同意后才调用
5. 调用 → 响应三分支：
   ✓ tid/pid 有值 → 成功，输出链接 {site}/forum.php?mod=viewthread&tid=<tid>
   ⏳ dshowmessageParam 含"审核" → 已提交待人工审核，如实告知，禁止宣称已发布
   🔒 提示"验证码/seccode" → 该版块开了发帖验证码，转告站长处理，禁止绕过
6. 输出结果与链接
```

**发帖参数**：`fid`（版块）、`subject`（标题）、`message`（正文，支持 Discuz! 代码如 `[b]` `[img]` `[url]`）。

**⚠️ 发帖/回帖的响应形态（实测）**：成功时 Discuz 返回的是**跳转 HTML 页**而非 JSON。判定与取值：
1. `Content-Type` 含 `text/html` → 发帖请求已被站点受理
2. 从 HTML 正则提取候选：`re.findall(r'viewthread&(?:amp;)?tid=(\d+)', raw)`
3. 用 `forumdisplay`（fid）列表对照，确认新帖 tid 后输出链接
4. 响应为 JSON 且 `dshowmessageParam` 有值时按上表三分支处理（审核/验证码/错误）
**回帖参数**：`tid`、`fid`、`message`。
**文章参数**：`catid`（栏目）、`subject`、`content`（HTML）。

## 五、错误处理与重试

| 症状 | 判定 | 处理 |
|---|---|---|
| `ret: 0` | 成功 | 继续 |
| `-102/-103` 类 token 错误 | Token 过期 | 重取 token → 原请求重试 1 次 |
| `-109 api is invalid` | 接口未导入/未授权 | 按〇之附提示站长，停止重试 |
| `-110` | Redis 未配置 | 停止，转告站长 |
| `-100 ~ -121` 其它 | 引擎错误 | 排查时钟偏差/nonce 重复/secret/应用权限；修正后重试 1 次 |
| **HTTP 403** | 站点 WAF（阿里云 ESA）拦截 | **确认 UA 为程序化 UA**（伪装浏览器 UA 必被 403）；保持默认 UA 重试 |
| 网络超时/连接错误 | 瞬时故障 | 指数退避 2s→4s→8s，最多 3 次 |
| `validateUnique` 拒绝 | 唯一性窗口 | 等待窗口期（登记为 10 秒）后重试 |

**总原则**：读类幂等可重试；**提交类（发帖/回帖/文章）仅在确认请求未到达时重试**——收到业务响应（哪怕报错）禁止重发，防重复发帖。

## 六、触发方式与输入输出

### 触发
"发帖/发个帖子/发布主题"、"回帖/回复 <主题>"、"发文章/发到门户"、"看论坛帖子/看版块"、"把这段内容推送到论坛/24krmb"。

### 输入输出

| 输入 | 来源 |
|---|---|
| 动作/标题/内容/fid/tid | 用户输入或共同撰写；缺失询问 |
| 站点/凭据/接口 | config.json（已预置，不再询问） |

| 输出 | 格式 |
|---|---|
| 发帖 | 「✅ 已发布《标题》：<链接>」 |
| 待审核 | 「⏳ 已提交，待管理员审核后可见」 |
| 失败 | 「❌ ret=<码> <含义>（已试 <N> 次）」+ 建议 |

## 七、安全红线

1. **发表前必须预览确认**；未经同意禁止调用写接口。
2. 拒绝违法违规、涉政敏感、垃圾广告、侵权内容。
3. **secret 不回显**（掩码前4后4）。
4. **UA 诚实**：禁止伪装浏览器 UA（会触发 WAF 403 且属不当行为）。
5. 连续发帖间隔 ≥10 秒。
6. 验证码/审核/权限拒绝 = 如实上报走人工，**禁止绕过**。
