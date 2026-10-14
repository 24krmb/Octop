---
name: publish-article
description: >-
  发布文章到 24krmb.com 门户（首页文章系统）。当用户或工作流需要把财经内容、
  收盘复盘、市场评论等以正式文章形式发布到 24KRMB 门户首页时使用此 skill。
  触发场景：用户说"发布到门户/发文章/发首页"；或定时任务的栏目发布环节（文章发布）。
  与 forum-api-publisher 的区别：本 skill 发布到门户文章系统（富文本 HTML，首页展示），
  forum-api-publisher 发布到论坛版块（Discuz BBCode，社区讨论）。
metadata:
  octop:
    emoji: "📰"
    requires: {}
    label:
      zh: "门户文章发布"
      en: "Portal Article Publisher"
    summary:
      zh: "把成稿内容以 HTML 富文本发布到 24krmb.com 门户文章系统（首页展示），支持栏目、来源署名与摘要。"
      en: "Publish finished content as rich-text articles to the 24krmb.com portal (homepage), with category, source attribution, and summary."
---

# 24KRMB 门户文章发布 Skill

## 这个 Skill 做什么

把**成稿的 HTML 富文本文章**发布到 24krmb.com **门户文章系统**（站点首页文章流），自动完成栏目归类、来源署名与摘要。

**与 forum-api-publisher 的分工**：

| | 本 skill（门户文章） | forum-api-publisher（论坛帖） |
|---|---|---|
| 目标位置 | 门户首页文章系统 | 论坛版块（各抒己见等） |
| 正文格式 | **HTML 富文本**（`<p><strong><table>` 等） | **Discuz BBCode**（`[b][size][list]`） |
| 展示形态 | 首页正式文章 | 社区讨论帖 |
| 鉴权 | IP 白名单 + API 密码 | 论坛账号登录 |

## 环境准备

- config.json 已内置 API 地址、发布密码与默认值（catid=193 财经资讯栏目）。
- **网络要求**：调用方 IP 必须在服务器白名单内（生产容器默认满足；本地开发环境会返回 403）。
- 无需论坛账号登录——API 直接走服务端发布。

## 基本调用格式

所有请求通过 `scripts/publish_article.py` 发出：

```bash
# 探活（验证可达与鉴权）
python3 scripts/publish_article.py check

# 发布门户文章（正文来自文件，推荐）
python3 scripts/publish_article.py post \
  --catid 193 \
  --title "【收盘复盘】标题（日期）" \
  --content-file /tmp/article.html \
  --summary "一句话摘要" \
  --from-name "24K-Claw AI"

# 或直接内联正文
python3 scripts/publish_article.py post --catid 193 --title "标题" --content "<p>HTML正文</p>"
```

#### 任何时候都要先成稿再发布：数据未就绪、内容未完成时不要调用本 skill。

## 正文规范（门户 HTML）

1. **只允许两种标签：`<h3>`（段标题）和 `<p>`（正文段落）**——不得使用 strong/br/table/ul 等其它任何标签。
2. 段标题格式：`<h3>【段名】</h3>`；每个正文段落一个 `<p>...</p>`；观察点等逐条内容每条一个 `<p>`。
3. **禁止** `<script>`、`javascript:`、`onerror=` 等危险标签（服务端拦截）。
4. 结构：`<h3>` 栏目标题段 → `<p>` 数据主体（带时点）→ `<h3>` 解读段 → 尾部风险提示 `<p>`。
5. 摘要（--summary）建议 60-100 字，用于门户列表页展示。
6. 发布前自查：正文只包含 `<h3>`、`<p>` 两种开闭标签。

## 输出判定

- 成功：`{"ok": true, "aid": 文章ID, "url": "portal.php?mod=view&aid=..."}`——**把 url 告知用户**。
- `code 403`：密码错误或 IP 不在白名单——如实反馈，不要重试。
- `code 400`：参数缺失——补全后重试一次。
- 网络异常：指数退避重试一次，仍失败则如实报告。

## 行为红线

1. 发布内容必须**成稿且数据完整**——半成品不出门。
2. **不发布**违法违规、涉政敏感、广告垃圾内容。
3. 金融内容附风险提示；不做收益承诺。
4. 频率自律：避免短时间内大量发布。
