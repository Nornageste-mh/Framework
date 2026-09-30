# A11yFramework

> **视觉小说的读屏无障碍补丁：可复用的平台层（L1）与契约层（L2）。**
>
> 从三个已发布的补丁（BelfryForAccessibility / TheNOexistenceNForAccessibility /
> TransparentHerForAccessibility）逆向固化而来。目标只有一个：
> **下一个补丁从第 0 天起，把平台层从「重写」变成「拷贝」**，
> 把工期集中到真正逐作不同的两件事 —— **文本清洗** 与 **补丁点挂载**。
>
> 设计依据与证据基础：`docs/无障碍补丁流水线.md`

---

## 这个仓库是什么

三个已发布仓库不是三个独立项目，而是**同一套代码的三次「复制—改名—局部改写」**：

| | belfry | noexistence | transparenther |
|---|---|---|---|
| 技术栈 | Mono / BepInEx 5 | IL2CPP / BepInEx 6 | Mono / BepInEx 5 |
| `Sapi.cs` / `Nvda.cs` 差异 | 基准 | 仅 `namespace` | 仅 `namespace` |
| `Speech.cs` 差异 | 基准 | 3 行 | 10 行（**删掉了诊断日志块**） |
| `UiNav.cs` 差异 | 基准 | 269–487 行 | 90–136 行 |
| `Plugin.<成员>` 跨文件引用 | 63 处 | 117 处 | 64 处 |

平台层三作几乎逐字节相同（差异只有 `namespace` 一行），真正逐作改写的只有
**文本清洗规则**和 **Harmony 补丁点**。既然事实上就是同一份，就把它固化成模板。

**复制式复用有一条已经应验的教训**（流水线 §1.3）：

> 平台层会**单向退化** —— 某一作修好的东西不会回流到其余两作，
> 反而会在下一次复制时被更旧的版本覆盖。

TransparentHer 就是这么丢掉 `[朗读]` 诊断日志块和 `UiNav.Diag()` 的。
本仓库存在的意义就是止住它：**接口固化，平台层只抄不改。**

> **仓库当前是私有的，这是临时状态。**
> 仓库里只有自己写的框架代码、第三方许可证文本与工程文档 ——
> **不含任何游戏资源、不含任何剧本原文、不含反编译产物**（见下面的「IP 与合规」），
> 所以具备公开的条件。公开与否、什么时候公开，由维护者决定。
> 真要公开之前，建议再跑一遍 `tools/compile_check.ps1` 与
> `grep -ri "剧本原文特征串" .` 这类检查，并把 `licenses/` 里
> 三作的 THIRD-PARTY-NOTICES 范例确认一遍（它们只是范例，不是最终发布用的清单）。

---

## 三层架构

```
┌──────────────────────────────────────────────────────────┐
│ L1 平台层（逐字节复用，永不逐作改写）                      │
│   platform/Speech.cs  后端链 Tolk→NVDA→SAPI + 定期重试    │
│   platform/Nvda.cs    nvdaControllerClient.dll 探测与朗读 │
│   platform/Sapi.cs    纯 P/Invoke + vtable 的 ISpVoice    │
│   platform/UiNav.cs   Unity Selectable 通用导航引擎        │
│   platform/KeyEdge.cs 带「松开闩锁」的单次按键检测（见下） │
│   platform/Repeat.cs  重读缓冲区 —— **唯一出口，逐作绕不过** │
├──────────────────────────────────────────────────────────┤
│ L2 契约层（每作一个薄适配文件，固化 ABI）                  │
│   contract/A11yHost.cs  共享层唯一可见的宿主              │
│   Plugin.cs（逐作）     BepInEx 入口：注册配置、注册补丁   │
├──────────────────────────────────────────────────────────┤
│ L3 逐作层（真正的开发工作量所在）                          │
│   TextProc.cs     原始文本 → 可朗读文本（本作专属规则）    │
│   Patches/*.cs    Harmony 补丁点（按反编译实查的方法名）   │
│   Choices/Qte/…   本作特有的交互形态                      │
└──────────────────────────────────────────────────────────┘
```

### L1 与逐作之间的接口就是 `A11yHost`

| 平台层原来写的 | 现在写的 | 语义 |
|---|---|---|
| `Plugin.Log` | `A11yHost.Log` | 共享层唯一日志出口 |
| `Plugin.CfgSpeechBackend` | `A11yHost.CfgSpeechBackend` | 语音后端（自动 / Tolk / NVDA / SAPI） |
| `Plugin.CfgDiagLog` | `A11yHost.CfgDiagLog` | 朗读诊断日志 |
| `Plugin.CfgVisibleOnly` | `A11yHost.CfgVisibleOnly` | 导航只含可见控件 |
| `Plugin.CfgSortByPosition` | `A11yHost.CfgSortByPosition` | 按屏幕位置排序 |
| `Plugin.CfgExcludeNames` | `A11yHost.CfgExcludeNames` | 人工排除名单（祖先链匹配） |
| `Plugin.CfgQuitConfirm` | `A11yHost.CfgQuitConfirm` | 危险操作二次确认 |
| `Plugin.CfgQuitNames` | `A11yHost.CfgQuitNames` | 需确认的控件名 |

平台层里**已经一处 `Plugin.` 引用都不剩**（`tools/compile_check.ps1` 会断言这件事）。

---

## 目录结构

```
A11yFramework/
├─ docs/
│  ├─ 无障碍补丁流水线.md          ★ 设计依据与全部证据索引
│  └─ templates/                   逐作文档骨架
│     ├─ 无障碍可行性验证.md       P0 的产物（一份文档，不是一个插件）
│     ├─ 测试问卷.md               P4 的载体（十节，第 8 节是硬要求）
│     ├─ 安装说明.md               发布包内文档（逐作重写）
│     └─ 常见问题.md               发布包内文档（跨作可复用）
│
├─ platform/                       L1 平台层（冻结层，逐作不改）
│  └─ Repeat.cs                    重读缓冲区：逐作层只能往里塞
│  ├─ Speech.cs
│  ├─ Nvda.cs
│  ├─ Sapi.cs
│  ├─ KeyEdge.cs                   ← 组装时从 belfry 提升上来，见 CHANGELOG
│  └─ UiNav.cs                     ← 已改成 internal static partial class
│
├─ contract/
│  └─ A11yHost.cs                  L2 契约层（每作一份，只填值不写逻辑）
│
├─ templates/
│  ├─ game/
│  │  ├─ Plugin.cs.template        BepInEx 入口 + 配置分组 + 补丁点骨架
│  │  ├─ TextProc.cs.template      文本清洗（每作必须重写）
│  │  ├─ UiNav.Game.cs.template    UiNav 的逐作区（别名表 + 姓名框探测）
│  │  └─ GameA11y.csproj.template  按 §3 路线选 Mono 或 IL2CPP 段
│  └─ probe/
│     ├─ ProbePlugin.cs.template   最小探针插件（转储运行时事实）
│     └─ Probe.csproj.template
│
├─ build/
│  ├─ build.ps1.template           下依赖 → 编译 → 组包（含 3 条发布前守卫）
│  ├─ release.ps1.template         打发布 zip
│  ├─ makezip.ps1.template         ★ 绝不要用 Compress-Archive，见下
│  └─ check-staged.ps1.template    提交前守卫（拦截不该入库的东西）
│
├─ probe/
│  ├─ run_probe.ps1.template       编译 + 部署 + 启动 + 收日志
│  └─ screenshot.ps1.template      截图取证
│
├─ licenses/                       三仓许可证并集（LGPL 要求随二进制附文本）
│  ├─ THIRD-PARTY-NOTICES.example-{belfry,transparenther}-mono.txt
│  ├─ THIRD-PARTY-NOTICES.example-noexistence-il2cpp.txt
│  └─ il2cppinterop-pr277.patch    IL2CPP 路线需要的上游补丁
│
└─ tools/
   ├─ new_game.py                  从本仓库生成一个新作的骨架
   ├─ compile_check.ps1            ★ 机械验证「平台层无游戏类型依赖」
   └─ assemble_from_sources.py     从三个源仓库重新组装 platform/ 与 licenses/
```

---

## 怎么用它开一个新作

### 1. 判定技术栈路线（第 0 个决策，决定后续一切）

看游戏目录里是哪一个：

| | **Mono 路线** | **IL2CPP 路线** |
|---|---|---|
| 判定 | `<Game>_Data\Managed\Assembly-CSharp.dll` | `<Game>_Data\il2cpp_data` + `GameAssembly.dll` |
| 参考实现 | transparenther（v0.5.9.0）、belfry | noexistence |
| BepInEx | **5.4.23.5** | **6.0.0-be.788** |
| 插件入口 | `BaseUnityPlugin` | `BasePlugin` |
| TFM | `netstandard2.1` | `net6.0` |
| 引用来源 | `<游戏目录>\<Game>_Data\Managed\*.dll` | `<游戏目录>\BepInEx\interop\*.dll` |
| 前置条件 | 无 | **必须先装 BepInEx 6 并跑一次游戏**生成 `interop\` |
| 额外配置 | — | `AllowUnsafeBlocks` + `<CodePage>65001</CodePage>` |

### 2. 生成骨架

```
python tools/new_game.py --ns MyGameA11y --game MyGame --exe MyGame.exe ^
    --guid mygame.a11y.reader --title 《我的游戏》 --route mono --out D:\work\MyGameA11y
```

它做这些事：拷 `platform/` + `contract/`、替换 `namespace`、套用 `templates/`
（去掉 `.template` 后缀、替换占位符）、建好 `mod/` + `probe/` + `tools/` 目录。
**生成之后平台层就不要再改了** —— 改了就不再是冻结层。

### 3. 填契约层

`Plugin.Awake` 里按顺序填空（`contract/A11yHost.cs` 的注释里有一份可抄的清单），
最后调一次 `A11yHost.Validate()` —— 漏填会写一行 Warning，而不是静默失效。

### 4. 逐作层（真正的工作量）

按依赖与风险递增的顺序做（流水线 §6 P3）：

1. **`TextProc.cs`** —— 先用 P0 导出的剧本表**离线**跑清洗规则，不进游戏就能验证
2. **台词朗读** —— 只挂「抓住当前台词」一个点，先把最短闭环跑通
3. **选项 + 编号选择 + 重读**
4. **限时选择** —— 只改 `ref delay`
5. **界面导航** —— `UiNav` 默认即可用，再按探针结果补 `NameAlias` 与排除名单
6. **本作特有形态** —— QTE / 手机 / 手书 / 特殊演出（**每作都会冒出一个**）

> ### 三条铁律（三作反复验证过的）
>
> 1. **不许猜方法名和对象名** —— 只能来自反编译实查（`ilspycmd`）或探针场景树转储。
> 2. **不许把「没实测」说成「已验证」** —— 未复测就写 **尚未实机复测**。
> 3. **别名表每一条都要有依据** —— 在注释里写明来自哪个方法 / 哪次探针。

---

## 平台层里已经固化的东西（照抄，不要重新发明）

### `Sapi.cs` —— Windows 内置语音，纯 P/Invoke

> **绝不要用** `Type.GetTypeFromProgID("SAPI.SpVoice")` + `InvokeMember`。
> Unity 的 Mono **没有实现** COM 后期绑定，实机日志是
> `SAPI 不可用: NotImplementedException`，表现是整局游戏一片安静。

已实机验证的 vtable 槽位（**错一位就会当场露馅**）：

```
0  QueryInterface        1  AddRef              2  Release
3  SetNotifySink         4  SetNotifyWindowMessage
7  SetNotifyWin32Event   10 SetInterest         11 GetEvents
16 Pause                 17 Resume              18 SetVoice
20 Speak                 21 SpeakStream         22 GetStatus
28 SetRate               29 GetRate             30 SetVolume
31 GetVolume             32 WaitUntilDone       33 SetSyncSpeakTimeout
```

- `CLSID_SpVoice = 96749377-3391-11d2-9ee3-00c04f797396`
- `IID_ISpVoice  = 6c44df74-72b9-4992-a1ec-ef996e0422d4`
- `COINIT_APARTMENTTHREADED = 0x2`，`CLSCTX_ALL = 0x17`
- **`SPF_ASYNC = 1` 必须置位**：SAPI 默认同步朗读，会阻塞 Unity 主线程导致游戏卡死
- `Stop()` = `Speak(NULL, SPF_ASYNC | SPF_PURGEBEFORESPEAK)`（`SPF_PURGEBEFORESPEAK = 2`）
- 初始化时**先读 rate/volume 验证 vtable 槽位** —— 错了在这一行露馅，
  而不是等玩家需要朗读时静默失败

### `Speech.cs` —— 后端链

- 自带 NVDA / SAPI 两级，**不强依赖 Tolk**（Tolk 官方只有 MSVC 工程、无预编译二进制）
- 后端选择可被配置钉死（排查用）；**钉死后不可用不会回退**，这是刻意的
- 初始化失败时把每个后端的结论串成一行日志（`Verdict()`），一眼看出「为什么全灭」
- 朗读抛异常 → 后端降级为 `None` 并允许重试，**绝不把异常抛给游戏主循环**

### `UiNav.cs` —— 通用导航引擎

引擎**几乎不引用任何游戏类型**，只认 UnityEngine / TMPro。机制（照抄）：

| 机制 | 实现 |
|---|---|
| 控件发现 | 每帧扫描 `Selectable`（**不依赖游戏提供任何列表**） |
| 分组 | 按控件在 Canvas 下的**顶层祖先**分组；组间按 `CanvasOrder → SiblingIndex` |
| 组内排序 | 字典序：**Row（屏幕上下）→ Left（屏幕左右）→ Path（渲染层级）** |
| 重扫 | **只扫「下一帧」**，且加**场景稳定门禁**（`SceneSettleSeconds = 1.5f`） |
| 位置换算 | `WorldToScreenPoint` 之后再分档（世界坐标 ≠ 屏幕像素） |
| 可见性 | `VisiblyClickable` + `CanvasGroup.alpha` |
| 退出确认 | `QuitConfirmArmed` / `QuitConfirmSeconds = 8f` |
| 输入角色 | `InputFieldRoleName` / `SliderValueText` / `PlaceholderText` |

> **绝不要对 `List.Sort` 的比较函数用「近似相等」当分支**
> （如 `Mathf.Abs(a.Left-b.Left) > 0.01f`）。它不满足传递性，
> 内省排序的结果是**任意的**，而且**不报错**。必须严格字典序。

---

## 逐作必须重新查的两件事

### 1. 文本清洗（`TextProc.cs`）

各作要处理的类别完全不同：

| 类别 | 《钟塔》 | 《不/存在的你，和我》 | 《透明的她与真实的我》 |
|---|---|---|---|
| 说话人包装 | `【 韩冬 】` → 剥掉 | — | — |
| 遮蔽名 | `【 ?  ? 】` → 念「？？？」 | — | — |
| 多人同框 | `【 许堇/韩冬 】` → 斜杠念成顿号 | — | — |
| 富文本 ruby | — | `<ruby="注">正文</ruby>`（**正文与旁注都要读**，本作题眼） | — |
| 抹除符号 | — | `█ ■ □` → 念「方块」 | — |
| 行内注释 | — | `;; @wait 2` 之后不朗读 | — |

> **ruby 那条是硬要求**：《不/存在的你，和我》的设计是「正文=表象、旁注=真相」，
> **只读正文会让盲人玩家错过题眼**。这不是优化，是无障碍完整性问题。

### 2. 补丁点（Harmony 挂载）

三作的「功能 → 挂载点」对应关系 —— **功能相同，方法名各不相同**：

| 功能 | belfry | noexistence | transparenther |
|---|---|---|---|
| 抓住当前台词 | `DialogueCommandExecutor.ExecuteDialogue` | `Naninovel.UI.RevealableText.set_Text` | `DialogueSceneManager.StartTyping(string)` |
| 选项出现 | `ChoiceHandler.ExecuteSelectionLogic` | `GenerateSelectionButton` | `DialogueSceneManager.ExecuteSelectionLogic` |
| 限时选择延长 | `ChoiceHandler.AutoDestroyAfterTime`（**只改 `ref delay`**） | （同） | `AutoDestroyAfterTime(ref float, DialogueScene)` |
| 手机消息 | `PhoneDialogueManager.AddMessage` | — | `PhoneDialogueManager.AddMessage(string,bool,PhoneDialogue)` |
| 拦截「推进剧情」 | `GameFlowManager.HandleAdvanceInput` | — | `DialogueButtonClicked` |
| uGUI submit 通路 | `StandaloneInputModule.SendSubmitEventToSelectedObject` | — | 常驻关 `sendNavigationEvents` |
| （本作特有） | — | QTE：`QTEUI` / `QTEScoreComponent` | 倒计时进度条 `FadingSlider.FadeSliderOverTime` |

**挂载点的唯一合法来源**：反编译实查（`ilspycmd`）+ 探针场景树转储。

### 组装时发现的两处（流水线 §1.2 的分类没覆盖到）

把平台层单独拉出来编译（`tools/compile_check.ps1`）之后，暴露出两个
「按文件清单分类、而不是按依赖分类」会漏掉的问题：

**1. `KeyEdge.cs` 其实属于 L1，不是 belfry 专有。**
流水线 §1.2 把它记成「belfry 的按键边沿检测」，暗示是逐作文件；
但平台层的 `UiNav.cs` 引用它 **14 处** —— 不带上它，引擎根本编不过。
本仓库把它提升为冻结层第 5 个文件。它只依赖 UnityEngine，没有任何游戏类型。

> 副产物：另外两作的 `UiNav` 是在 `Update` 里直接写
> `Input.GetKeyDown(...)` 的，没有 KeyEdge 这一层。
> 因为本仓库统一采用 belfry 的 UiNav，所以逐作**必须**一起带上 `KeyEdge.cs`。

**2. `UiNav` 的很多成员是「引擎用、逐作算」的，不能按块切。**
拆 partial 时按注释区块把「姓名输入框」整段搬进逐作区，结果引擎的 `Scan()`
每次重扫都要调 `_inputRoles.Clear()` —— 声明搬走了，引擎就编不过（CS0103）。
最终定下的切法是：

- **声明留在引擎**（`_inputRoles`），因为引擎会直接用它
- **只有「怎么算出这个值」留在逐作区**（`InputFieldRoleName`，里面写死了游戏类型名）

> 教训：拆分平台层的依据是**依赖方向**，不是注释里的区块标题。
> 这也是为什么一定要有 `compile_check.ps1` —— 这种错靠读代码很难发现。

### 一条必须逐作判定的「正确答案」

`EventSystem.sendNavigationEvents` 的处理**必须每作单独判定**，
判据是「游戏自己有没有用 `SetSelectedGameObject` / 选中态」：

- **belfry 不能常驻关** —— 游戏自己就在用 EventSystem 选中态（横条导航、面板提交、
  焦点修正、存档槽 `ISubmitHandler`）。只在导航模式确实要接管那一下按键时才掐。
- **transparenther 应常驻关** —— 游戏全代码无 `SetSelectedGameObject`；
  不关的话，鼠标点过的按钮会在按空格推进剧情时**被重复点击**。

> 两作给出了两个**相反的**正确答案。这正是「平台层不能无脑复制到引擎行为」的例子。

---

## 陷阱清单（可直接当 review checklist）

### 通用

| # | 陷阱 | 正确做法 |
|---|---|---|
| G1 | **对迭代器方法用 Prefix 返回 false 跳过** → 它返回 `null`，调用方是 `StartCoroutine(...)` | 迭代器方法只能改 `ref` 参数 |
| G2 | **Harmony 前缀的参数名必须和运行时一致，不是和反编译结果一致** | 写错名字 → `PatchAll` 抛异常，**其他补丁仍生效**，症状极隐蔽 |
| G3 | **`Enum.TryParse("0")` 成功但得到 `KeyCode.None`**（数值 0），不是 `Alpha0` | 按键配置项先自己映射单个数字 |
| G4 | **别用 PowerShell 文本 cmdlet 改源码**（PS 5.1 按 ANSI/GBK 读无 BOM 的 UTF-8，中文变乱码） | 用 `[System.IO.File]::WriteAllText(..., UTF8Encoding($true))` |
| G5 | **`.ps1` 含中文且无 BOM → PS 5.1 按 GBK 解码 → 语法错误** | 构建脚本存 UTF-8 **带 BOM**；或发布脚本**纯 ASCII** |
| G6 | **BepInEx 日志是缓冲异步刷盘（约 2 秒一次）** | 用脚本读日志驱动自动化测试时必须等够时间 |
| G7 | **`BepInPlugin` 版本号含字母 → 静默跳过整个插件** | 只用纯数字四段；构建脚本里加守卫 |
| G8 | **`BepInPlugin` 版本必须与 `.csproj` 的 `<Version>` 一致** | 构建脚本里校验，不一致直接 exit 1 |
| G9 | **`List.Sort` 比较函数不满足传递性 → 结果任意且不报错** | 严格字典序，不许「近似相等」分支 |
| G10 | **世界坐标 ≠ 屏幕像素** | 先 `WorldToScreenPoint` 换算再分档 |
| G11 | **界面重扫不能定时**（激活按钮后 0.35 秒重扫会撞上场景销毁 → **无 C# 异常的原生崩溃**） | 只扫「下一帧」+ 场景稳定门禁 |
| G12 | **找特定控件别用词边界正则**（`\b(exit|quit)\b` 对 `ExitButton` / `QuitGame` 两头都错） | 拿实查到的对象名**全等比较** |

### IL2CPP 专属（三类「静默失败」，全部不报错）

| # | 陷阱 | 正确做法 |
|---|---|---|
| I1 | **`s.transform is RectTransform` 恒为 `false`，`as Toggle` 恒为 `null`** | Il2CppInterop 给的是包装对象，必须走 `TryCast<T>()` |
| I2 | **托管数组传给原生方法会被拷贝，写不回来** | 用 `Il2CppStructArray<Vector3>` |
| I3 | **猜对象名**（`GameObject.Find("QTEPanel")`） | 引用游戏自己的类型 + `FindObjectOfType`（类型引用是**惰性解析**的） |

### 两条不许越过的红线

> **1. 无障碍层绝不能扩大可达范围。**
> 语义是「把本来能看到/能操作的东西，用朗读与键盘**等价地**呈现」，不是「顺手加功能」。
>
> - **限时选择的倒计时只能拉长，不能取消** —— 到点会走这一批最后一条的
>   `ToNumber`，也就是「什么都不做」的沉默分支。**取消 = 删掉一个剧情分支。**
> - **不可用的选项补丁故意不点** —— 游戏把该项标成不可用，点它 = 越过游戏自己的分支控制。
> - **剧透闸门** —— 无障碍朗读会「读出」视觉上一闪而过的信息，
>   必须与正常玩家在同一时刻获得同一信息。
>
> **2. 发布前必须验证「关掉补丁时游戏本身行为不变」**（测试问卷第 8 节）。

---

## 构建与打包（`build/`）

构建脚本流程（5 步，照抄骨架）：

```
1/5  检查游戏目录（找不到 <Game>.exe 就 exit 1，提示用 -GameDir 指定）
2/5  获取 BepInEx（本机 dl\ 缓存 → 跨仓库缓存 CacheDir → 联网下载）
3/5  获取 nvdaControllerClient.dll（x64）
4/5  编译 + ★发布前守卫
5/5  组装 package\
```

**★发布前守卫（三条，必须保留）**：

1. `BepInPlugin` 版本号必须是合法 `System.Version`（否则 BepInEx 静默跳过整个插件）
2. `BepInPlugin` 版本必须等于 csproj 的 `<Version>`
3. `dotnet build -c Release -v minimal -nowarn:MSB3277 -p:<Game>GameDir="$GameDir"`

**两条打包红线**：

- **绝不要用 `Compress-Archive`** —— Windows PowerShell 5.1 会委托给
  .NET Framework 的 `ZipFile.CreateFromDirectory`，它用 `Path.DirectorySeparatorChar`
  生成条目名，于是每个条目都是 `BepInEx\core\某个.dll` 这种反斜杠形式。
  ZIP 规范要求 `/`；Windows 资源管理器和 7-Zip 容忍反斜杠，
  **Linux/macOS 的 `unzip` 不容忍** —— 会解出一堆名字里带反斜杠的平铺文件。
  用 `makezip.ps1` 手工构造条目。
- `nvdaControllerClient.dll` **同时放两处**：`BepInEx\plugins\` **和包根**
  —— Mono 的 `DllImport` 会**先查应用目录**。

**不分发**：`BepInEx\interop` / `unity-libs`（首次运行时按本机游戏自动生成）、
`BepInEx\config\<guid>.cfg`（玩家自己的配置）。

---

## 尚未验证的部分（诚实纪律）

**本仓库的结论全部是静态的源码层结论。没有一行代码在游戏里跑过。**

| 做过的验证 | 怎么做的 | 证明了什么 |
|---|---|---|
| 平台层**无游戏类型依赖** | `tools/compile_check.ps1`：编译 `platform/` + `contract/` 时**不引用 `Assembly-CSharp`** | **已跑通：0 错误 0 警告** ⇒ 平台层确实只依赖 UnityEngine / TMPro / BepInEx |
| 平台层**无 `Plugin.` 引用** | 组装脚本断言 + `compile_check.ps1` 静态检查 | 接口确实已经全部改指 `A11yHost` |
| 平台层**能挂上逐作 partial** | 用一份最小 `UiNav.Game.cs` 占位实现参与编译 | partial 拆分的接口是完整的 |
| 三作差异矩阵 | 对 `main` 克隆后按 SHA256 逐文件比对 + 归一化 `namespace` 后 `diff -U0` | 见流水线 §1.1 |
| `tools/new_game.py` 能生成干净的骨架 | 冒烟测试：生成 54 个文件，**无残留占位符、无上一作标识**，`.ps1` 带 BOM，csproj 按路线正确裁剪 | 骨架生成这一环是通的 |
| `tools/assemble_from_sources.py` 可复现 | 重跑一遍后 `git status` 为空 | 平台层与 licenses/ 是**逐字节可复现**的，不是一次性手改的结果 |

| **没做过的验证** | 说明 |
|---|---|
| 平台层在游戏里跑起来 | 需要实机 + 读屏软件，见 `docs/templates/测试问卷.md` |
| `build/`、`probe/` 脚本**真能跑通** | **没有**在任何一个新作上试过（需要游戏目录 + BepInEx + 实机） |
| 「取最完整的一份」在 Mono 与 IL2CPP 两条路线上都成立 | 只是源码合并，**不等于**在任意一作上编得过、跑得起来 |
| `UiNav` 的 partial 拆分没有行为改变 | 拆法是机械的（可见性一个都没动），但**没有实机回归** |

> 按流水线 §6 P4 的**诚实纪律**：CHANGELOG 里明确标注「尚未实机复测」的条目是允许的，
> 把未验证的东西标成已验证是**不允许**的。

---

## IP 与合规

### 证据的 IP 红线（流水线 §6 P1 原文）

> 本仓库只放**不含剧本文本**的证据。
>
> 游戏截图与含台词原文的会话日志**故意不入库** —— 画面本身就是游戏美术资源，
> `[朗读]` 日志行就是剧本原文。仓库的「不包含任何游戏资源」必须**字面成立**。

推论（必须遵守）：

- 探针插件**不记录任何台词文本**，只写类型名、方法名、对象名与控件标签
- `[朗读]` 诊断日志的产出物（`LogOutput.log`）**不得入库**
- 需要复核原始日志时，在本机按 README「如何复现分析」重跑，**不提交**

### 合规

发布包里除了自己的插件 DLL，还有十来个第三方二进制（BepInEx、UnityDoorstop、
HarmonyX、Mono.Cecil、MonoMod、NVDA Controller Client）。
**BepInEx 官方 zip 里一个许可证文件都不带**，所以这些得自己列。
完整清单与范例见 `licenses/THIRD-PARTY-NOTICES.example-*.txt`。

**一条容易记反的事**：

> **BepInEx 5 是 MIT，BepInEx 6 才是 LGPL-2.1。**
> 同一个仓库，`master` 分支是 v6、`v5-lts` 分支是 v5，凭印象很容易记反。

**LGPL 组件怎么合规**：`winhttp.dll`（UnityDoorstop）与
`nvdaControllerClient.dll`（NVDA Controller Client）以 LGPL-2.1 授权，
二者都以**未经修改的独立动态库**形式随包分发，既没改它们、也没静态链接进自己的程序集 ——
即 LGPL-2.1 第 6(b) 条所说的「使用共享库机制」，因此**不触发源码分发义务**，
但仍须随包附上许可证全文 + 显著声明 + 源码获取途径。

---

## 许可

本仓库的**补丁框架代码与文档**（`platform/`、`contract/`、`templates/`、`build/`、`docs/`）
由本项目的维护者编写，供制作同类无障碍补丁时复用，采用 [MIT 许可](LICENSE) 发布。
附加的署名要求、非官方声明与免责条款见 [NOTICE.md](NOTICE.md)。

`licenses/` 下是**第三方组件**的许可证文本，版权归各自作者所有；
其中 `THIRD-PARTY-NOTICES.example-*.txt` 是三作的原样范例，
**逐作发布时必须重写**（组件清单与版本不同）。

**本仓库不含任何游戏资源、不含任何游戏的剧本原文、不含任何反编译产物。**

---

## 相关仓库

| 仓库 | 技术栈 | 作为什么参考 |
|---|---|---|
| [TransparentHerForAccessibility](https://github.com/Nornageste-mh/TransparentHerForAccessibility) | Mono / BepInEx 5 | **最成熟**（v0.5.9.0），界面导航引擎的参考实现 |
| [TheNOexistenceNForAccessibility](https://github.com/Nornageste-mh/TheNOexistenceNForAccessibility) | **IL2CPP** / BepInEx 6 | IL2CPP 路线唯一参考；构建/发布/合规最完备 |
| [BelfryForAccessibility](https://github.com/Nornageste-mh/BelfryForAccessibility) | Mono / BepInEx 5 | 结构最新；最接近「新作起步形态」 |

> 本仓库是这三作的公共部分，**不是任何一款游戏的补丁**，装进游戏不会有任何效果。

---

## 许可证

本仓库的**代码与文档**采用 [MIT 许可](LICENSE) 发布。
附加的**署名要求、非官方声明与免责条款**见 [NOTICE.md](NOTICE.md)。

简要说明：

- **可自由使用、修改、再分发**（含商用），但须标注出处 —— 本仓库地址与作者
  Nornageste-mh；若你做了修改，须注明「已修改」，不得让人误以为修改版出自原作者。
- **本项目为非官方第三方工具**：本仓库是独立开发的通用无障碍框架（视觉小说读屏补丁的平台层与契约层），不是任何一款游戏的补丁，与任何游戏开发商、发行商均无隶属关系，未获其授权或背书。本仓库不含任何游戏资源、剧本原文或反编译产物。
- **按「现状」提供，不承担任何责任**：因使用本软件导致的游戏存档损坏、游戏崩溃、
  账号受限、或与游戏厂商及任何第三方产生的争议与索赔，作者与贡献者均不负责。
  是否使用请自行判断并自担风险。

第三方组件的许可与出处详见 [NOTICE.md](NOTICE.md)。
