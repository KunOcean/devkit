# implementations

同一功能在其他编程语言下的实现，用于学习与技术对比。规范见
[`docs/multi-language.md`](../docs/multi-language.md)。

> **只做安全修复，不跟进功能迭代。** 功能演进只发生在 `projects/` 下的 HTML 版。

## 进度

| 语言 | core | full |
|---|---|---|
| Rust | 待开始 | 待开始 |
| Go | 待开始 | 待开始 |
| Python | 待开始 | 待开始 |
| TypeScript | 待开始 | 待开始 |
| C# | 待开始 | 待开始 |
| C++ | 待开始 | 待开始 |

## 目录

```
<语言>-core/<项目>/    纯逻辑内核，CLI 形态
<语言>-full/<项目>/    完整功能，含图形界面
```

`core` 与 `full` 用目录区分、版本号相同；EXE 与 Web 两种形态用扩展名区分；
DevKit 的 10 个皮肤变体用文件名后缀区分，其中 `_All` 为九皮肤合并版。

## 工具链

构建所需工具链位于 `D:/dai/ccworks/toolchains/`，不在系统 PATH。
构建脚本应先 source 仓库根的 [`toolchains.env`](../toolchains.env)。

已验证可产出 EXE 的版本：

| 语言 | 版本 | 验证产物 |
|---|---|---|
| Rust | 1.99.1 (GNU target) | 1.2 MB |
| Go | 1.23.4 | 2.2 MB |
| Python | 3.14.4 + PyInstaller 6.22.3 | 9.1 MB |
| C++ | GCC 16.2.0 (w64devkit) | 2.5 MB |
| C# | .NET 8.0.404 | 65 MB（单文件自包含） |
| TypeScript | Node 22.11.0 (SEA) | 待验证 |
