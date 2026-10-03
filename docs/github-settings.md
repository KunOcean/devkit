# GitHub 仓库设置手册（bmdy1145/devkit）

> 本手册供在网页端配置本仓库时逐项对照。
>
> - GitHub 简体中文界面的实际译文与本文不一定逐字相同，故每项均给出「中文 → 英文」对照，两边对不上时以英文为准。
> - 仓库设置、Rulesets、Actions 配置这几类**没有 API 接口**，只能网页端点；仓库内容（分支、提交、PR、文件）则由 Claude Code 走 PR 流程提交，见 `docs/branching.md`。

## 当前实际状态

| 项 | 状态 |
|---|---|
| `main` 分支保护 | **已开启**（GitHub 报告 `protected: true`） |
| 绕过列表 | 已加入「仓库管理员 → Repository admin」 |
| 仓库所有者 | `@bmdy1145`（admin）、`@nahida38454`（write） |
| Actions | 尚未确认是否已启用及是否已有成功运行记录 |

**绕过的实际后果**：`@bmdy1145` 是仓库管理员，可绕过规则直推；`@nahida38454` 只是 write 角色，**绕不过**，它的推送一律受规则约束。这正是把绕过限定为"仓库管理员"而非"所有人"的意义。

---

# 首次启用时的前置顺序（顺序不能乱）

若要在一处全新仓库或规则被重置后重新配置，按此顺序：

| 顺序 | 动作 | 理由 |
|---|---|---|
| 1 | 先让 `.github/` 下的 CODEOWNERS 与工作流进入 `main` | Code Owners 从 base 分支读取，必需状态检查也要求该工作流在默认分支出现过 |
| 2 | 确认工作流在 `main` 上成功跑过一次（合并触发，或手动 `workflow_dispatch`） | 只有跑过一次，它才会出现在「必需状态检查」的可选列表里 |
| 3 | 再做下面的手册 A、B | —— |
| 4 | 最后做手册 C，其中「需要通过状态检查」要留到 C 的最后一步 | 见文末注意 3 |

---

# 手册 A · 拉取请求设置

**路径**：仓库页 → **Settings（设置）** → 左侧 **General（常规）** → 向下滚到 **Pull Requests（拉取请求）**

| 项（中文 → 英文） | 建议 | 理由 |
|---|---|---|
| 允许合并提交 → Allow merge commits | 取消勾选 | 不让 merge commit 把分支中间态带进 main |
| 允许压缩合并 → Allow squash merging | 勾选，默认提交信息选「拉取请求标题 → Pull request title」 | 每个 PR 在 main 上只留一个提交 |
| 允许变基合并 → Allow rebase merging | 取消勾选 | 与压缩合并二选一，避免历史形态混杂 |
| 自动删除头部分支 → Automatically delete head branches | 勾选 | 堆叠 PR 会积很多分支，自动清掉 |
| 允许自动合并 → Allow auto-merge | 取消勾选 | 会绕过人工把关 |
| 始终建议更新拉取请求分支 → Always suggest updating pull request branches | 勾选 | 分支落后时给提示，减少冲突 |

此类开关即时生效，无需保存。

---

# 手册 B · 操作（Actions）设置

**路径**：**Settings（设置）** → 左侧 **Actions（操作）** → **General（常规）**

### B-1 操作权限 → Actions permissions

- 选 **允许所有操作 → Allow all actions and reusable workflows**
- 想更严可选 **允许指定操作 → Allow *owner* actions and reusable workflows**，白名单只填 `actions/checkout@*`
  （代价：以后每加一个官方 action 都要回来放行）
- **不要选「禁用 → Disabled」**，选了工作流永远不跑

### B-2 分叉拉取请求工作流 → Fork pull request workflows

- 建议：**首次贡献者需要批准 → Require approval for first-time contributors**
- 更省事但安全性最低：**从分叉拉取请求运行工作流 → Run workflows from fork pull requests**
- 不建议：**所有外部协作者都需要批准 → Require approval for all outside collaborators**（每次都要手点）

### B-3 工作流权限 → Workflow permissions

- 选 **读取仓库内容 → Read repository contents and packages permissions**
- **允许 GitHub Actions 创建和批准拉取请求 → Allow GitHub Actions to create and approve pull requests** 取消勾选

B-1 至 B-3 改完各自点 **Save（保存）**。

---

# 手册 C · 给 main 加规则集

**路径**：**Settings（设置）** → 左侧 **Rules（规则）** → **Rulesets（规则集）** → 右上 **New ruleset（新建规则集）** → **New branch ruleset（新建分支规则集）**

> 若左侧只有 **Branches（分支）** 而没有 **Rules（规则）**，说明是旧版分支保护页，字段位置不同，需另行对照。

### C-1 表单上半部

| 字段（中文 → 英文） | 填什么 |
|---|---|
| 规则集名称 → Ruleset Name | `main-protection` |
| 强制执行状态 → Enforcement status | **活动 → Active** |
| 绕过列表 → Bypass list | 本项目实际填 **仓库管理员 → Repository admin**（理由与后果见「当前实际状态」） |
| 目标分支 → Target branches | **添加目标 → Add target** → **包含默认分支 → Include default branch**，或 **按模式包含 → Include by pattern** 填 `main` |

### C-2 分支规则 → Branch rules

| 勾选项（中文 → 英文） | 子选项 |
|---|---|
| **合并前需要拉取请求 → Require a pull request before merging** | **必需的批准数 → Required approvals** 填 `1`；勾 **推送新提交时忽略过期批准 → Dismiss stale pull request approvals**；勾 **需要代码所有者审阅 → Require review from Code Owners**；不要勾 "Require approval of the most recent reviewable push" |
| **合并前需要解决对话 → Require conversation resolution before merging** | 无 |
| **需要通过状态检查 → Require status checks to pass** | 勾选后在下拉里选工作流 job 名 **版本号与结构一致性**；此项留到最后做 |
| **需要线性历史记录 → Require linear history** | 无 |
| **阻止强制推送 → Block force pushes** | 无 |
| **限制删除 → Restrict deletions** | 无 |

其余项（Require deployments、Require signed commits 等）不勾。最后点 **Create（创建）**。

---

# 手册 D · 给版本标签加保护（可选）

**Rules → Rulesets → New ruleset → New tag ruleset（新建标签规则集）**

| 字段 | 填什么 |
|---|---|
| 规则集名称 | `tag-protection` |
| 强制执行状态 | 活动 → Active |
| 目标标签 → Target tags | **按模式包含 → Include by pattern**，填 `v*` |
| 勾选规则 | **限制删除 → Restrict deletions**、**阻止强制推送 → Block force pushes** |

---

# 附录 · 把 GitHub 界面切成中文

右上角头像 → **Settings（设置）** → 左侧最下 **Appearance（外观）** → **Preferred language（首选语言）** → **简体中文** → **Save（保存）**

---

# 三个必须注意的坑

1. **绕过列表填「仓库管理员」只对 admin 生效**。本仓库只有 `@bmdy1145` 是 admin，`@nahida38454` 是 write，绕不过规则。若希望它也保留直推能力，需把它加入绕过列表或提升为 admin——但那样等于给它开了后门，需权衡。
2. **必需的批准数只能是 1**。仓库只有两个有权限的账号，PR 必然由其中一人提出，另一个最多给 1 个批准；填 2 会让所有 PR 永久卡死。
3. **「需要通过状态检查」必须最后开**。工作流还没在 `main` 上成功跑过一次之前就勾它，所有 PR 会卡在一个永远不会出现的检查上。
