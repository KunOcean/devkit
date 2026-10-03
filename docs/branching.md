# 分支与 PR 约定

> 本文件由项目根 `CLAUDE.md` 与 `.repo-git/CLAUDE.md` 通过 `@` 导入，会话启动时自动加载。
> 规则只维护在这一处，改这里即两处同时生效，不要在两份 CLAUDE.md 里各写一份。

## 流程

改动不直推 `main`。流程为：

1. 在 `.repo-git/` 建 feature 分支
2. 推送到**两个远端**（缺一不可，原因见「堆叠 PR」）：

   ```
   git push -u kun <分支>
   git push -u origin <分支>
   ```

3. 提 PR：`head = KunOcean:<分支>`，`base = bmdy1145:main`
4. 由仓库主在网页版审阅并合并
5. 合并后清理两个远端上的该分支——GitHub 的「自动删除头部分支」只删同仓分支，来自 fork 的 PR 不会删 fork 上的分支，上游那份更不会自动删

## 两个远端

| 远端 | 仓库 | 职责 |
|------|------|------|
| `kun` | https://github.com/KunOcean/devkit.git | 下游 fork，PR 的 `head` 分支所在地 |
| `origin` | https://github.com/bmdy1145/devkit.git | 权威仓，Pages 站点 https://bmdy1145.github.io/devkit/ 挂在它名下，也是 `main` 的跟踪上游。**feature 分支也要在这里放一份**，否则堆叠 PR 无法指定 base |

## 堆叠 PR

**前提：feature 分支必须同时推到两个远端。**

跨仓 PR 的 `base` 必须是**上游（bmdy1145/devkit）里真实存在的分支**。只推到 fork 的分支，上游看不到，无法充当 base——GitHub 会直接拒绝创建 PR，报 `PullRequest.base (invalid)`（2026-10-03 实测踩到过）。

若上一个 PR 尚未合并而下一版已经开始：

- 新分支基于**上一个未合并的分支**；
- 新旧两个分支**都要推到 `kun` 与 `origin`**；
- 提 PR 时 `base` 填**上一个分支的名字**（上游已有同名分支，可以指定），不是 `main`；
- 上一个 PR 合并后，GitHub 会自动把下一个 PR 的 `base` 改回 `main`，diff 自动收敛为增量；
- **禁止**让两个分支都从 `main` 分叉——那样第二个 PR 会把第一批改动再算一遍，或直接回退已审查过的内容。

若两批改动确实互不重叠，也可以不堆叠、各自从 `main` 分叉，只要各自的新分支都推两个远端即可；但一旦有重叠，必须走上面的堆叠路径。

## 红线

- 不得 approve 自己提出的 PR（GitHub 硬性禁止）；合并权始终在仓库主手上。
- 直推 `main`（含推送 `origin`）仍需逐次明确授权；未获授权不得推送。
- 两个远端的推送权限均已证实可用（`kun` 与 `origin` 各推过 feature 分支）。若某次推送意外被拒，立即告知，**不得改推另一个远端绕过**。

## 为什么不用仓库设置解决

GitHub 仓库设置里没有"上一版未合并就不许开下一版"这类开关：

- **Merge queue** 只管把**已批准**的 PR 依次合并，未批准的进不了队列；
- **Branch protection / Rulesets** 只管能否直推 `main` 与合并门槛；
- **Auto-merge** 管单个 PR 在条件满足后自动合并；
- **Update branch** 方向相反，是把 base 合进 head。

堆叠关系只能靠建分支时选对 `base` 来管，属协作约定，不属仓库设置。
