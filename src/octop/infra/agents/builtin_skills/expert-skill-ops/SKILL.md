---
name: expert-skill-ops
description: 必须用于对内置专家（experts/library/）和 SKILL 的增、删、改、查操作指引——包括删除内置专家、添加内置专家、给专家添加/移除技能、添加平台内置技能（builtin_skills）、修改专家欢迎语/快捷提问，以及排查"实例缺少技能"问题。关键词：删除专家、添加专家、专家技能、内置技能、SKILL 绑定、模板库。Also use when the user asks to add/remove bundled experts or skills.
metadata:
  octop:
    emoji: "🎭"
    label:
      zh: "专家与技能运维"
      en: "Expert & Skill Ops"
    summary:
      zh: "增删改查内置专家与 SKILL 的标准操作手册（三处联动、种子机制、验证方法）。"
      en: "Standard ops runbook for bundled experts and SKILL binding (three-touchpoint rule, seeding, verification)."
---

# 专家与 SKILL 运维手册

本技能指导对 Octop 内置专家库（`experts/library/`）与 SKILL 体系做增删改查。所有路径相对仓库根。

## 一、体系速记

- **专家 = 目录**：`src/octop/infra/agents/experts/library/<expert-id>/`，必需 `manifest.json`，可选 `SOUL.md`/`IDENTITY.md`/`HEARTBEAT.md`/`USER.md`（人格）+ `skills/<slug>/SKILL.md`（自带技能）+ `agents/*.md`（子代理）
- **文件即绑定**：manifest 里没有 skill 引用字段——目录下存在 `skills/<slug>/` 就会随创建实例种子生效
- **SKILL = 目录 + SKILL.md**：frontmatter（name/description 必须含触发词；`metadata.octop`: emoji/label.zh+en/summary.zh+en）+ 正文指引
- **运行时**：deepagents skills middleware 扫描工作区 `.octop/skills/`（system_files_path 前缀）与 `_builtin_skills/`，把 frontmatter 清单注入 system prompt；模型按需 `read_file` 读全文或用 `/slug` 触发；`SkillFilterMiddleware` 按 agent 级禁用集合过滤
- **落点注意**：专家技能种子进 Agent 工作区的 **`.octop/skills/<slug>/`**（不是工作区根 `skills/`）；平台内置技能进 **`_builtin_skills/`**

## 二、删除内置专家（三处联动，缺一处留残）

1. `git rm -rq src/octop/infra/agents/experts/library/<expert-id>`（模板本体）
2. `git rm 头像`：`dashboard/public/experts/avatars/<expert-id>.svg`（若存在）
3. 清 `src/octop/infra/agents/experts/catalog.py` 中 `_FALLBACK_BUNDLED_AVATAR_IDS` 集合里的该 id
4. 验证：重启后端 → `GET /api/experts`（带 Bearer token）确认列表已无该 id

## 三、添加内置专家（反向三处联动）

1. 建 `library/<expert-id>/`：`manifest.json`（id/label/description/welcome_message/icon_name/color/prompt_files/quick_prompts/task_examples，双语 zh+en）+ 人格 md + 可选 `skills/`
2. 头像 `dashboard/public/experts/avatars/<expert-id>.svg`（可选）
3. `catalog.py` 的 `_FALLBACK_BUNDLED_AVATAR_IDS` 加入该 id（若提供了头像）
4. 重启后端 → `GET /api/experts` 验证

## 四、给专家增删自带技能

- **加**：`library/<expert-id>/skills/<新slug>/SKILL.md`（+ references/）
- **删**：删对应 `skills/<slug>/` 目录
- **生效范围**：只影响**之后创建**的实例；已有实例需在对话中用 skill-manager 更新工作区，或删掉重建实例
- **排查"实例缺技能"**：先确认模板里有（`discover_seed_paths` 会包含 `skills/**`），再查实例工作区 `.octop/skills/<slug>/` 是否存在；不存在 = 创建时种子未生效，重建实例即可

## 五、添加平台内置技能（所有 Agent 生效）

1. 建 `src/octop/infra/agents/builtin_skills/<skill-id>/SKILL.md`（+ scripts/ 可选）
2. 重启 octop 服务
3. 验证：Agent 工作区出现 `_builtin_skills/<skill-id>/`
- 注意：`_builtin_skills/` 是受保护目录（`builtin_skills/__init__.py::is_octop_builtin_skills_path`），运行时不要直接改里面的文件——改源码重建
- ⚠️ 引擎层技能（`octop_harness` 包 `builtin/skills/`）不归本仓库管，改不了也不应改

## 六、改欢迎语 / 快捷提问 / 图标

改 `library/<id>/manifest.json` 对应字段（`welcome_message` / `quick_prompts` / `icon_name` / `color`）→ 重启。**只影响新创建的实例**——欢迎语在创建时种子到实例 `.octop/manifest.json`，已有实例不改。

## 七、验证与排查清单

- 目录扫描：`GET /api/experts`（401 = 缺 Bearer token；登录 `POST /api/auth/login` 拿 `access_token`）
- 种子清单干跑：容器内 python 调 `ExpertCatalog(default_library_root()).refresh()` 后查 `catalog.get('<id>').files`
- 实例工作区：`/data/.octop/agents/<AGENT_ID>/`（人格文件在根，技能在 `.octop/skills/`，平台内置在 `.octop/_builtin_skills/`）
- 创建实例：`POST /api/agents` **body 必须含 `name`**（仅 template_name 会 422）
- 删除实例（清理测试产物）：`DELETE /api/agents/<agent_id>`
