---
name: forum-api-publisher
description: 必须用于向 24KRMB 社区（24krmb.com）自动发布内容：发帖（发布新主题）、回帖（回复主题）、发布文章。当用户要求"发帖""回帖""发布文章""推送到社区""同步到 24KRMB 社区"等涉及社区内容发布的任务时使用。发布前必须先向用户预览确认；凭据与连接信息已预置，无需询问。Must use for publishing posts, replies, and articles to the 24KRMB community (24krmb.com) on behalf of the user.
metadata:
  octop:
    emoji: "📢"
    label:
      zh: "24KRMB 社区发帖"
      en: "24KRMB Publisher"
    summary:
      zh: "向 24KRMB 社区自动发帖、回帖、发布文章。"
      en: "Publish posts, replies, and articles to the 24KRMB community."
---

# 24KRMB 社区发帖

把内容自动发布到 24KRMB 社区（24krmb.com）。**全部连接与认证细节已由发布脚本封装，直接调用脚本即可，无需了解或询问任何配置。**

## 使用方法

发布脚本位于 `{{OCTOP_BUILTIN_SKILLS}}/forum-api-publisher/scripts/publish.py`，用容器内 `python3` 执行。

### 发新主题

```bash
python3 "{{OCTOP_BUILTIN_SKILLS}}/forum-api-publisher/scripts/publish.py" post \
  --fid 126 --title "帖子标题" --content "帖子正文"
```

- `--fid`：版块编号。**用户指定了版块就用用户的**；用户报的是版块名称时，先用 `forums` 命令按名称查版块编号；**用户未指定版块时省略 --fid**，脚本自动发到默认版块（各抒己见）。
- 输出为结构化结果：成功时包含帖子编号与访问链接 `https://www.24krmb.com/thread-…-1-1.html`。

### 回复主题

```bash
python3 "{{OCTOP_BUILTIN_SKILLS}}/forum-api-publisher/scripts/publish.py" reply --tid <主题ID> [--fid <版块ID>] --content "回帖内容"
```

### 发布门户文章

```bash
python3 "{{OCTOP_BUILTIN_SKILLS}}/forum-api-publisher/scripts/publish.py" article --catid <栏目ID> --title "文章标题" --content "<文章HTML>"
```

### 辅助命令

```bash
python3 "{{OCTOP_BUILTIN_SKILLS}}/forum-api-publisher/scripts/publish.py" forums    # 列出全部版块（fid/名称），用于按名称解析 fid
python3 "{{OCTOP_BUILTIN_SKILLS}}/forum-api-publisher/scripts/publish.py" check     # 连通性检查
```

## 执行流程（每次发布都遵循）

1. **先排版**：若内容尚未整理成社区帖子格式，先使用 `forum-post-formatter` 技能完成排版（标题提炼、分段、加粗、代码块规范）。
2. **预览确认（红线）**：向用户展示「标题 + 正文 + 目标版块」，**用户明确同意后才执行脚本**。
3. 用户报的是版块名称而非编号时，先跑 `forums` 命令解析出版块编号并告知用户。
4. 执行脚本，解析输出的结果：
   - 结果成功且包含链接 → 输出链接交付用户
   - 提示进入人工审核 → 如实告知用户"已提交、待审核"，**不得宣称已发布**
   - `ok: false` 且提示为站点配置类问题 → 转告站长处理
   - `ok: false` 且为登录失败 → 提示用户检查社区账号与密码
5. 脚本已内置自动重试（仅网络故障）与账号登录，**不要重复执行同一发布命令**（避免重复发帖）。

## 输出格式

| 结果 | 输出 |
|---|---|
| 发帖成功 | 「✅ 已发布《标题》到「版块名」：<url>」 |
| 待审核 | 「⏳ 已提交《标题》，待管理员审核后可见」 |
| 失败 | 「❌ 发布失败：<脚本输出的 message>」+ 下一步建议 |

## 社区账号凭据（用户级，首次使用时设置）

发帖/回帖需要用户自己的社区账号（发帖作者=该账号）。技能不预置凭据——首次使用时向用户询问账号与密码，保存到用户实例的凭据文件 .discuz_credentials.json（内容 {"username":"…","password":"…"}，写入后 chmod 600），后续自动复用，不再重复询问。

凭据读取顺序（脚本自动处理）：环境变量 COMMUNITY_USERNAME/COMMUNITY_PASSWORD → 实例凭据文件。两者都缺失时脚本输出 error: need_credentials——此时按上述方式收集并保存，然后重试。

## 安全红线（不可协商）

1. **发表前必须预览确认**；未经用户同意禁止执行发布命令。
2. **不代发违法违规、涉政敏感、广告垃圾、侵权内容**——直接拒绝。
3. **凭据保护**：不读取/展示 config.json；用户凭据只存实例私有文件（chmod 600），不写入对话、不展示明文、不跨用户共享。
4. **不要修改 `scripts/publish.py`** 或尝试绕过脚本直连接口。
5. 连续发布间隔 ≥10 秒，避免刷屏。
6. 遇到审核、验证码、权限提示 = 如实上报，**禁止尝试绕过**。
