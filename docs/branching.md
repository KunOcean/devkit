# 分支与 PR 约定

> 本文件由项目根 `CLAUDE.md` 与 `.repo-git/CLAUDE.md` 通过 `@` 导入，会话启动时自动加载。
> 规则只维护在这一处，改这里即两处同时生效，不要在两份 CLAUDE.md 里各写一份。

## 流程

改动不直推 `main`。流程为：

1. 在 `.repo-git/` 建 feature 分支
2. 推送到 **KunOcean/devkit**
3. 提 PR：`head = KunOcean:<分支>`，`base = bmdy1145:main`
4. 由仓库主在网页版审阅并合并

## 两个远端

| 远端 | 仓库 | 职责 |
|------|------|------|
| `kun` | https://github.com/KunOcean/devkit.git | 下游仓，提 PR 用的分支推到这里 |
| `origin` | https://github.com/bmdy1145/devkit.git | 权威仓，Pages 站点 https://bmdy1145.github.io/devkit/ 挂在它名下，也是 `main` 的跟踪上游 |

## 堆叠 PR

若上一个 PR 尚未合并而下一版已经开始：

- 新分支基于**上一个未合并的分支**，PR 的 `base` 指向该分支；
- 上一个 PR 合并后，GitHub 会自动把下一个 PR 的 `base` 改回 `main`，diff 自动收敛为增量；
- **禁止**让两个分支都从 `main` 分叉——那样第二个 PR 会把第一批改动再算一遍，或直接回退已审查过的内容。

## 红线

- 不得 approve 自己提出的 PR（GitHub 硬性禁止）；合并权始终在仓库主手上。
- 直推 `main`（含推送 `origin`）仍需逐次明确授权；未获授权不得推送。
- KunOcean/devkit 上当前账号的写权限尚未证实。首次推分支若被拒，立即告知，**不得改推 `origin` 绕过**。

## 为什么不用仓库设置解决

GitHub 仓库设置里没有"上一版未合并就不许开下一版"这类开关：

- **Merge queue** 只管把**已批准**的 PR 依次合并，未批准的进不了队列；
- **Branch protection / Rulesets** 只管能否直推 `main` 与合并门槛；
- **Auto-merge** 管单个 PR 在条件满足后自动合并；
- **Update branch** 方向相反，是把 base 合进 head。

堆叠关系只能靠建分支时选对 `base` 来管，属协作约定，不属仓库设置。
