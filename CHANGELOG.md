# CHANGELOG

## 版本方案

| 形式 | 含义 |
|---|---|
| `v0.x.y` | 现行官方序列，用 **annotated tag** |
| `v1.0.0` | 目标是「功能完整且经实机验证稳定」，在此之前不发布 |
| 纯数字四段（`0.1.0.1`） | 版本号的**唯一合法形式**，见下 |

> **版本号必须是纯数字四段。**
> `BepInPlugin` 的版本串如果含字母（例如为了表达「0.5.8a」写成 `0.5.8a`），
> BepInEx 会判定 `version is invalid` 并**静默跳过整个插件** ——
> 日志里只有一行 Warning，表现是模组完全没加载、游戏里一片安静，极难排查。
> 想表达「第五版修订」就写 `0.5.8.1`。

## 版本清单

| 版本 | 日期 | 要点 |
|---|---|---|
| 0.1.0.0 | 待填 | 从三个已发布仓库逆向固化的平台层 + 契约层初版 |

---

## 0.1.0.0 — 把「复制—改名—局部改写」固化成一次性的平台层

### 做了什么

从三个已发布仓库（BelfryForAccessibility / TheNOexistenceNForAccessibility /
TransparentHerForAccessibility）的 `main` 分支逆向出可复用的部分，按
《无障碍补丁流水线》§2 的三层架构重新落位：

- **L1 平台层**（`platform/`）——`Speech.cs` / `Nvda.cs` / `Sapi.cs` / `UiNav.cs`
  逐字节复用。源取三作里**最完整**的一份，缺的东西已经补回来了（见下）。
- **L2 契约层**（`contract/A11yHost.cs`）—— 固化平台层与逐作代码之间的接口，
  止住「某一作修好的东西不会回流」的单向退化。
- **骨架**（`templates/` / `build/` / `probe/` / `licenses/`）—— 从三作拷来并占位符化。

### 顺手修掉的三个已知缺陷（流水线 §1.3）

三个仓库互相抄，抄丢了东西，而且因为没有回流机制，丢掉的东西一直没补回来。
本版按「谁有就用谁的」原则补回：

1. **`Speech.cs` 的 `[朗读]` 诊断日志块** ——
   TransparentHer 那份被删掉了（去掉 namespace 后 diff 出 −10 行），
   结果那一作**无法在日志里逐条核对朗读内容**。本版取 belfry / noexistence 的版本。
2. **`UiNav.cs` 的 `Diag()` 全套**（定义 + 4 处调用）——
   TransparentHer 那份全删了，导航状态迁移无法排查。本版取 belfry 的版本。
3. **`UiNav.cs` 的 `IsExcluded()` 祖先链排除机制** ——
   TransparentHer 没有，无法按对象名排除噪音控件。本版取 belfry 的版本。

> 注：「取最完整的一份」这件事本身**没有实机验证过**（本仓库不含游戏，
> 也没有跑过游戏）。它只是静态的源码合并，结论是「源码层面前三者齐了」，
> **不等于**「在任意一作上编得过、跑得起来」。见 README 的「尚未验证的部分」。

### 新增的设计：`UiNav` 拆成 partial

流水线 §1.2 把 `UiNav.cs` 定性为「平台层·引擎通用 + 逐作配置」，
但三个仓库里它是**一整个文件**，所以每作复制过去都得在里面翻找该改哪几行。
本版按这条定性做了机械拆分：

- `platform/UiNav.cs` —— 引擎（冻结，逐作不改）
- `templates/game/UiNav.Game.cs.template` —— 逐作区，两块：
  1. `NameAlias` 别名表（对象名 → 中文，「每一条都要有依据」）
  2. `NameInputManagerTMP` 姓名框探测（游戏类型名写死在反射里）

拆法是 `internal static class UiNav` → `internal static partial class UiNav`，
成员可见性一个都没动。

### 组装过程中揪出来的两处（流水线 §1.2 的分类没覆盖到）

这两处都是**把平台层单独拉出来编译**之后才暴露的（`tools/compile_check.ps1`），
按文件清单读代码是发现不了的：

1. **`KeyEdge.cs` 提升为 L1。** 流水线 §1.2 把它记成「belfry 的按键边沿检测」，
   但平台层的 `UiNav.cs` 引用它 **14 处** —— 不带上它引擎编不过（CS0103）。
   已作为冻结层第 5 个文件放进 `platform/`。
   注意：另外两作的 UiNav 是直接写 `Input.GetKeyDown(...)` 的，没有这一层；
   本仓库统一采用 belfry 的 UiNav，所以逐作**必须**一起带上 KeyEdge.cs。
2. **`_inputRoles` 的声明挪回引擎侧。** 按注释区块拆 partial 时，
   「姓名输入框」整段被搬进了逐作区 —— 但引擎的 `Scan()` 每次重扫都要
   `_inputRoles.Clear()`。定下来的切法是「声明留引擎，算法留逐作」。
   教训：拆分的依据是**依赖方向**，不是注释里的区块标题。

### 验证结果

`tools/compile_check.ps1` 在装了《钟塔》的本机上跑通：

```
[4/4] dotnet build（不引用 Assembly-CSharp）
      已成功生成。
          0 个警告
          0 个错误
PASS  平台层只依赖 UnityEngine / TMPro / BepInEx，**没有游戏类型依赖**。
```

这条证明的是「平台层确实没有游戏类型依赖」——
**不证明**它挂进游戏之后行为正确。

### 尚未实机复测

- 平台层**没有在游戏里跑过**。本版只做到「源码合并 + 编译通过」。
- **编译验证的范围**见 `tools/compile_check.ps1`：它只编译 `platform/ + contract/`，
  **故意不引用 `Assembly-CSharp`** —— 编得过就证明平台层没有游戏类型依赖，
  但**不证明**它挂进游戏后的行为正确。要证明那个，得按 §6 P4 的测试问卷实机走一遍。
- `build/`、`probe/` 里的脚本是**占位符化的模板**，没有在任何一个新作上跑过。
