---
name: discuz-post-formatter
description: 当用户要求把内容整理成 24KRMB.COM 社区帖子格式时必须使用。适用于 24krmb.com 社区发帖前的排版：标题提炼、分段重组、重点加粗、代码块规范，输出可直接粘贴到 BBcode 编辑器的成稿。Also use when the user asks to format content as a forum post.
metadata:
  octop:
    emoji: "📝"
    label:
      zh: "社区帖子排版"
      en: "Post Formatter"
    summary:
      zh: "把任意内容排版成 24K 社区可直接发布的帖子格式。"
      en: "Format any content into a ready-to-post Discuz forum thread."
---

# 24KRMB 社区帖子排版

你负责把用户提供的内容整理成适合发布在 Discuz X5 社区（24krmb.com）的帖子。

## 排版规则

1. **标题**：给出一个 不超过20 字以内的标题，概括核心内容，不加书名号。
2. **开头**：开门见山，1-2 句话说明"这篇帖子讲什么、适合谁看等"。
3. **正文**：不要使用过多的换行。禁止灌水、广告、营销等。
4. **结尾**：附一句互动引导（如"有问题回帖留言"）。
5. **结尾**：附一句互动引导（如"有问题回帖留言"）。
6. **禁止**：使用 HTML 标签、表情包刷屏、营销话术、夸大标题。

## 输出格式

坚决不直接把 MD 格式文本输出，必须先转换为 BBCode 格式。

1. Markdown → DiscuzX 5.0 BBCode 对照表
| 功能 | Markdown 写法 | BBCode 写法 |
|------|--------------|------------------------|
| 加粗 | `**文字**` | `[b]文字[/b]` |
| 斜体 | `*文字*` | 不要使用斜体 |
| 删除线 | `~~文字~~` | `[s]文字[/s]` |
| 一级标题 | `# 标题` | `[size=6][b]标题[/b][/size]` |
| 二级标题 | `## 标题` | `[size=5][b]标题[/b][/size]` |
| 三级标题 | `### 标题` | `[size=4][b]标题[/b][/size]` |
| 链接 | `[文字](URL)` | `[url=URL]文字[/url]` |
| 图片 | `![描述](URL)` | `[img]URL[/img]` |
| 行内代码 | `` `代码` `` | `[code]代码[/code]` |
| 代码块 | ` ```代码``` ` | `[code]代码[/code]` |
| 引用 | `> 文字` | `[quote]文字[/quote]` |
| 无序列表 | `- 项目` | `[list][*]项目[/list]` |
| 有序列表 | `1. 项目` | `[list=1][*]项目[/list]` |
| 表格 | `\| a \| b \|` | `[table][tr][td]a[/td][td]b[/td][/tr][/table]` |
| 分割线 | `---` | 不要使用分割线 |

2. Markdown 原生不支持、但论坛特有的功能
| 功能 | DiscuzX 5.0 BBCode 写法 |
|------|------------------------|
| 文字居中 | `[align=center]文字[/align]` |
| 字体颜色 | `[color=red]文字[/color]` |
| 视频/音频 | `[media=mp4,500,375]URL[/media]` |
| 隐藏内容（回复可见） | `[hide]内容[/hide]` |
| 免费信息 | `[free]内容[/free]` |

## 排版完成后

排版成稿可直接使用 `forum-api-publisher` 技能自动发布到 24KRMB 社区（无需用户手动复制粘贴）——用户表达发布意图时主动衔接。
