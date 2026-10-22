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
| 0.2.4.0 | 2026-10-22 | 实机导航日志暴露的三个平台层缺陷：**行标签被未激活控件挡掉**（`HasOtherSelectable`/`FirstTextOutside` 只认可见控件）、**alpha≈0 的预制体占位入列**（`VisiblyClickable` 加 `CanvasGroup` 门槛）、**未命名控件没有降级行为就直接激活**（`IsUnnamedLabel` + 复用 `CfgUnknownConfirm` 二次确认，关掉则硬阻止）；compile_check 通过（0 警告 0 错误） |
| 0.2.3.0 | 2026-10-22 | 用户要求导航开关「全程焦点也能用」：新增 `platform/GlobalKeys.cs`（Win32 `GetAsyncKeyState` 轮询，不装钩子、不注入）+ `A11yHost.UseGlobalKeys`（默认 false，只增不改）；`KeyEdge` / `Hotkey` 改为「`Input` 或全局」并集；导航键定为 **Ctrl+Alt+主键盘加号**（`Hotkey.Parse` 支持 `Plus`/「加号」，强制 Shift+Equals，小键盘加号不算）；compile_check 通过（0 警告 0 错误） |
| 0.2.2.0 | 2026-10-22 | 用户反馈的两个问题：**读不到文字时不再念对象名/类型名/ID**（分层标签 + 结构化语义降级 + 降级确认），**导航开关改为可配组合键**（`A11yHost.NavTogglePressed` 钩子，本作 `Ctrl+Alt+G`）；另修 **IL2CPP 下 16 处 `as`/`is`/`GetType()` 判组件类型的阻断级 bug**；compile_check 通过（0 警告 0 错误） |
| 0.2.1.0 | 2026-10-16 | **争渡 dll 自动定位**（读注册表登记的安装目录）+ **旧 dll 自动跳过**（`InitTTS=1` → 换下一份候选）+ `A11Y_ZDSR_DIR` 支持多目录；自助检 **71 条** |
| 0.2.0.0 | 2026-10-15 | **新增争渡读屏（ZDSR）后端**（`platform/Zdsr.cs`）+ **运行中切换后端**（`platform/Hotkey.cs` / `Speech.CycleAvailable`）+ 机械自检 `tools/zdsr_selftest/`（64 条断言，桩 DLL 驱动，不需要真读屏；0.2.1.0 增至 71 条） |
| 0.1.1.0 | 2026-09-27 | **重读缓冲区提升为 L1**（`platform/Repeat.cs`）+ `lint_repeat.ps1` 静态断言：逐作层绕不过去。同一个坑在四个仓库里踩了两次 |
| 0.1.0.2 | 2026-09-27 | **修 `.gitignore` 的行内注释 bug** —— 11 条规则全部静默失效，第三方二进制与发布 zip 可以照常入库（《妹控计划》发布时实测中招） |
| 0.1.0.1 | 2026-09-27 | 界面标签四钩子（文本噪声 / 逐作标签 / 组名 / 组序）+ 进组播报全组总览；修掉新作骨架的两个致命 bug（漏拷 KeyEdge.cs、csproj 注释里的连续减号） |
| 0.1.0.0 | 待填 | 从三个已发布仓库逆向固化的平台层 + 契约层初版 |
| 未发版 | 2026-10-21 | 公开前修订：免责声明与许可口径、探针文本转储默认关闭、脚本通用化与本机路径脱敏 |

---

## 0.2.4.0 — 实机导航日志暴露的三件事：**看不见的不算、读不出的不点、占位的不念**

### 一、行标签被「未激活的控件」挡掉

实机日志（设置面板）：`[UiNav] 未命名控件：类型=按钮 原始名=Btn_Swtich_Off` ——
同一行明明有 `text_Name`（「游戏时不显示」）。

根因在 `platform/UiNav.cs` 的 `HasOtherSelectable`：
`GetComponentsInChildren<Selectable>(true)` 把**未激活**的 `ToggleItem`/`Toggle`
也算成「这一行里还有别的控件」→ 判定该行是「面板」→ `FirstTextOutside` 直接
`return ""`，行标签永远拿不到，开关只能读成「未命名按钮」。

修法：

- `HasOtherSelectable` 只统计 `activeInHierarchy` 且不 `AlphaHidden` 的控件；
- `FirstTextOutside` 的候选文字同样只收 `activeInHierarchy`、不 alpha 隐藏的；
- 候选文字上溯找「别的控件」时改用新增的 `VisibleControlOn(t)`：
  未激活 / 透明的控件不再是阻断项。

### 二、alpha≈0 的预制体占位按钮进了导航列表

实机日志：`[组 2] Lilith/Canvas/PlayerLine 项数=16`，条目是
`Root/Root (3)/Button (3)` 这类占位。它们是 **active 的**，矩形在 Canvas 内，
UI 射线也能打中 —— 旧 `VisiblyClickable` 的两道判据全过，于是被当成可操作项。

新增 `AlphaHidden(Transform t)`：从控件往上最多 12 层，任意一层
`CanvasGroup.alpha ≤ 0.05`（`AlphaVisibleThreshold`）即视为看不见。
`VisiblyClickable` 第一道就过这个门槛 —— 比发射线便宜，也纠正了
「射线打得到所以可见」的错误推理。

不新增配置：仍受 `CfgVisibleOnly` 控制；关掉它就回到旧行为（诊断对比用）。

### 三、未命名控件「没有降级行为就激活」

用户原话：**「中途没有降级行为就执行了这个操作」**。实机日志：
`[UiNav] 激活原始对象：路径=.../Button (2) 来源=own 质量=Bound` ——
占位按钮还能捡到一段占位文字（`Bound`），旧实现只对 `Semantic`/`Raw` 做二次确认，
于是第一次回车就直接点了。

- 新增 `IsUnnamedLabel(Selectable)`：标签只能落到「未命名<类型>，第 N 项」
  （`Quality == Semantic`，或 `Raw` 且 `CfgSpeakRawName` 关闭）时为真。
- 回车/空格提交时：
  - 未命名 + `CfgUnknownConfirm` 开（默认）→ 第一次只念
    「<描述>。未命名控件，已阻止操作。再按一次确认；按别的键取消。」，
    **不调 `Activate`**；第二次才真正激活（8 秒窗口，复用降级确认状态机，
    不新增配置）；
  - 未命名 + `CfgUnknownConfirm` 关 → 硬阻止、永不激活，原始路径写 Diag；
  - 有中文标签或逐作 `GameLabelOf` 标签（`Bound`/`Nearby`）→ 行为不变，
    不会误伤正常按钮。
- 原始对象名/路径仍然只进 Diag 日志，不进朗读。

### 四、兼容性与边界

- 纯增量：`AlphaHidden` / `VisibleControlOn` / `IsUnnamedLabel` 都是私有新函数，
  现有成员签名与配置项不变。
- 收紧只作用于「隐藏控件 / 透明占位」：前三作里这类控件本来就不该念、不该点。
- 唯一的行为变化：未命名控件不再第一次就激活。`CfgUnknownConfirm=false`
  是「更安全」而不是「回到旧行为」；要恢复直接激活，得靠逐作的
  `GameLabelOf` / `GameGroupName` 或可见文字把标签补起来。
- 逐作标签与组名（`UiNav.Game.cs`）不在本版范围，由逐作层处理。
- `compile_check.ps1` 通过（0 警告 0 错误）；实机复验由 Lead 重启游戏完成。

---

## 0.2.3.0 — 窗口拿不到焦点时，按键怎么办：**全局按键兜底 + 主键盘加号**

### 一、问题：不是绑定错了，是窗口永远没有键盘焦点

《不/存在的莉莉丝》的 Unity 窗口：`class = UnityWndClass`、
`exstyle = 0x080800B0`（`WS_EX_NOACTIVATE | LAYERED | TOOLWINDOW | TOPMOST |
TRANSPARENT`）。默认「单击穿透」模式下它**不能激活**；实机连试三次
`SetForegroundWindow` / `AttachThreadInput` / `SwitchToThisWindow` 都拿不到焦点
（前台始终是 Program Manager / 浏览器），期间发 `Ctrl+Alt`、`Tab` 没有任何
UiNav 日志。结论：**`UnityEngine.Input` 读不到任何键**，UiNav 的导航开关、
方向键、回车、数字键全部静默失效。这不是绑定问题，是焦点依赖。

### 二、做法：`GetAsyncKeyState` 轮询（不装钩子、不注入）

新增 `platform/GlobalKeys.cs`（L1，只引 `System.Runtime.InteropServices` + `UnityEngine`）：

- 只用 `[DllImport("user32.dll")] GetAsyncKeyState` **轮询**当前按键状态；
  **不装全局钩子**（`SetWindowsHookEx`）、**不做 DLL 注入**、不碰游戏线程。
- 不依赖窗口焦点：前台是任何程序都能读到 —— 这正是需求。
- `GetAsyncKeyState` 只回答「现在是否按住」，没有按下沿：边沿由
  `GlobalKeys.Pressed` / `KeyEdge.Pressed` 的静态表自己算（`held && !prev`）。
- 可用性一次性探测：非 Windows / 没有该导出 → `Available = false` **且永不重试**，
  调用方自动退回纯 `Input`，不抛异常、不刷日志。
- KeyCode→VK 表覆盖 Tab / Return / KeypadEnter / Space / 方向键 / PageUp / PageDown /
  Home / End / 字母 / 主键盘数字 / 小键盘数字与符号 / 常用符号（含 `Equals` `Minus`
  `KeypadPlus`）/ 左右修饰键 / F1–F12；未映射的键一律 `false`（宁可读不到，不猜错）。
- 全局模式下 `Input.anyKeyDown` 也失效，`ModifierChordDown` 的「按住期间按了别的键」
  改用「武装时快照 + 快照外新按键」判定（`FillOtherKeySnapshot` / `AnyNewOtherKeyHeld`）。

### 三、开关：`A11yHost.UseGlobalKeys`（只增不改，默认 false）

- `contract/A11yHost.cs` 新增 `public static bool UseGlobalKeys`，默认 `false`，
  逐作填 `true`；`Clear()` 里恢复 `false`。
- 打开后 `KeyEdge.Pressed` / `Hotkey.Down` 的 held/down 取「`Input` 或全局」并集，
  其余语义（闩锁、修饰键必须精确匹配）一条不动。
- **接线方向保持 platform → contract**：契约层只放 bool，平台层每帧懒同步
  （`GlobalKeys.Reading → SyncWithHostSwitch`），不让契约层反向引用平台层。
- `Hotkey.cs` 通过 `GlobalHeld` / `GlobalPressed` 两个委托接收全局状态，而不是直接
  引用 `GlobalKeys` —— 它必须能被 `tools/zdsr_selftest` 单文件编译（只 Include
  `Zdsr.cs` + `Hotkey.cs`）。

> **安全边界**：`GetAsyncKeyState` 读的是**整机**按键状态，与前台是谁无关。
> 打开后玩家在别的程序里按导航键也会触发。所以这是逐作显式开关，不是平台默认。

### 四、导航键改为「Ctrl+Alt+主键盘加号」

- `Hotkey.Parse` 新增 `Plus` / 「加号」token：主键映射到 `KeyCode.Equals`，
  并**强制要求 Shift 按住**（主键盘 `+` 本来就是 Shift+Equals）。
  于是：**小键盘加号（`KeypadPlus`）不触发**、**纯 `Ctrl+Alt`（没有主键）不触发**、
  `Ctrl+Alt+字母`（游戏自带的 9 条热键）也不会被误判 —— 主键对不上。
- 想读小键盘加号就显式写 `KeypadPlus`；VK 表里 `Equals` / `Minus` / `KeypadPlus`
  三个键都在，方便实机验证「只认大键盘加号」。
- README 的「`Hotkey.cs` —— 按键描述解析」「`GlobalKeys.cs` —— 窗口拿不到焦点时的
  按键兜底」「尚未验证的部分」三处同步更新。

### 五、兼容性与未验证

- 默认关闭：前三作不填 `UseGlobalKeys`，`GlobalKeys.Reading` 恒 `false`，
  `KeyEdge` / `Hotkey` 的新分支整体跳过，行为与 0.2.2 逐字节一致。
- `framework/tools/compile_check.ps1` PASS：静态断言 6 项 ok、引用 9 个程序集
  **不含 `Assembly-CSharp.dll`**、`dotnet build` **0 警告 0 错误**。
- **尚未实机复测**（诚实纪律）：`GetAsyncKeyState` 的按下沿自算、「加号只认主键盘、
  小键盘不触发」、「窗口没焦点时真的能切导航」三项都需要实机按一遍
  —— 目前只有编译与静态语义检查。

---

## 未发版 — 公开前修订（2026-10-21）

仓库即将由私有转为公开，本次做了对外发布前必须做的修订。**不改任何行为**，
只改「公开后会不会被人指出问题」的部分：

### 一、声明与口径

- `README.md` 顶部**新增免责声明**（非官方 / 无隶属未获授权 / 不含游戏资源与剧本原文 /
  需自备正版 / 反对盗版传播 / 收到权利人异议即调整或下线），完整条款仍在 `NOTICE.md`。
- `README.md` 原「**仓库当前是私有的，这是临时状态**」整段改写为公开口径。
- 「不含反编译产物」这句**精确化**：不含反编译**生成的完整代码文件（含类型定义与方法体）**；
  仓库里出现的方法名 / 类名 / 字段名与调用序列是说明补丁点与论证行为所必需的**互操作事实**，
  不属于反编译产物。原来的写法容易被读成「连反编译得到的事实也没有」，那是不成立的。
- `README.md` 的「证据的 IP 红线」里，探针只记 `(len=N)` 的说法与
  `ProbePlugin.Walk` 的实际行为不一致，已按下面第二节改为如实描述。
- `docs/无障碍补丁流水线.md` 的「BepInEx 是 MIT，不是 LGPL」**改掉** ——
  那是被当作合规指引照抄的一行，正确说法是 **BepInEx 5 是 MIT、BepInEx 6 才是 LGPL-2.1**
  （与本仓库 README 的「合规」节一致）。

### 二、探针的文本转储

- `templates/probe/ProbePlugin.cs.template` 的 `Walk()` 原本会把控件上的文字截 60 字写进日志，
  与同文件「绝不把台词原文写进日志」的注释、README 的声明都冲突。
  现在**默认关闭**（新增 `ProbePlugin.DumpUiText = false`），注释也改成如实描述。
- 探针日志文件名从固定的 `probe_belfry.log` 改为 `probe_{{PROCNAME}}.log`；
  插件 GUID 从 `belfry.a11y.probe` 改为 `{{GUID}}.probe`。

### 三、通用化（新作不该被上一作的标识绑住）

- `probe/run_probe.ps1.template`：`$P` 改为 `$PSScriptRoot`；启动游戏改为启动
  `<游戏目录>\<可执行文件>`，不再硬编码《钟塔》的 Steam AppID（必须经 Steam 启动的
  游戏按注释里的一行换成 `steam://rungameid/<AppID>`）。
- `probe/screenshot.ps1.template`：`$Out` 默认值改为 `$env:TEMP\shot.png`。
- `build/build.ps1.template`：`$CacheDir` 默认值改为 `$env:A11Y_CACHE`（未设即不启用缓存，
  相应判断都加了空值守卫）；用法注释里的本机路径改为占位。
- `build/release.ps1.template`：同上（注释）。
- `templates/probe/Probe.csproj.template`：BepInEx / 0Harmony 的 `HintPath` 改为
  `{{GAMEDIR}}\BepInEx\core\*.dll`（引用游戏目录里已装好的 BepInEx），
  不再指向作者本机的另一个仓库。
- `tools/compile_check.ps1`：`-GameDir` 默认值改为 `$env:A11Y_GAMEDIR`；
  `tools/new_game.py` 生成新作时按 `--gamedir` 覆写该默认值（`--gamedir` 默认改为空，
  不给则保留 `<游戏目录>` 占位）。

### 四、脚本与文档里的本机路径

- `tools/assemble_from_sources.py`：`--study` 默认值改为 `$env:A11Y_STUDY` → `~/a11y-study`；
  **新增 `--refresh-generated`**：`build/`、`probe/`、`templates/probe/` 下的模板已改为
  手工维护，默认不再被重新生成覆盖（要重新生成才加这个开关）。注意它们只做了**字符串**
  占位化（`{{TITLE}}` / `{{GUID}}` / `{{PROCNAME}}`），探针里的类型名与成员仍是上一作的
  示例，换作时要重写。另新增 `--refresh-platform`：`platform/` 自 0.2.x 起有手工演进
  （`Repeat.cs`、争渡后端等），默认不重生成。这样重跑只在 `licenses/` 上有写操作，
  「重跑一遍 `git status` 为空」仍成立。
- 文档里作者本机的绝对路径（`docs/无障碍补丁流水线.md` 末尾的克隆位置、
  `README.md` 的示例输出目录、`new_game.py` 的 docstring 示例）全部改为占位/相对路径。
- `.gitignore` 增 `__pycache__/` 与 `*.pyc`（跑 `py_compile` 会留下）。
- `tools/zdsr_selftest/run.ps1` 与 `ZdsrSelfTest.csproj` 不再硬编码游戏目录：改用
  `-GameDir` / 环境变量 `A11Y_GAME_DIR`（直接构建 csproj 时用 `/p:UnityManaged=…`
  或 `A11Y_UNITY_MANAGED`），gcc 走 `-Gcc` / `A11Y_GCC` / PATH。
- **有意保留的一条字面量**：`tools/assemble_from_sources.py` 的 SUBS 映射源必须与源仓库
  里的字符串逐字一致（否则 `--refresh-generated` 匹配不到、模板不会替换），所以那里保留了
  `D:\Steam\steamapps\common\钟塔 Belfry`。它是游戏安装路径、不含用户名；上一条所列的
  是本机工作目录，与此不同。

### 五、公开前对抗式审核发现的缺口（同日补）

- **争渡 ZDSRAPI 专有 DLL 的许可缺口**：三份 `licenses/THIRD-PARTY-NOTICES.example-*.txt`
  是 2026-09 的快照，只列了开源组件，没列随包兜底的争渡专有 DLL；而 `platform/Zdsr.cs`
  与本文档都记着「发布包里会附一份」。已把三份范例同步为三个姊妹仓的当前版本
  （新增「争渡读屏 ZDSRAPI」一项 —— 两份 Mono 范例是第 8 项、IL2CPP 那份是独立小节；
  明写不属于 MIT、未取得书面许可；范例给出的再分发依据
  来自争渡官方 API 文档，属姊妹仓各自的分发决定，**不代表本框架的建议**），
  `NOTICE.md` 组件表补一行并在 §6 说明本仓库**不随附**该 DLL，
  `README.md`「合规」节与 `docs/无障碍补丁流水线.md` 的「照抄」清单同步补上。
- `platform/Zdsr.cs` 的注释原先把「随包兜底」写成推荐做法，与它自己引用的官方原话
  「尽量不要复制到自己程序目录」并列会自相矛盾。改为「兜底是可选项、由分发者自负授权
  责任、本仓库不提供该 DLL」。
- 探针的说话人字段（`nameText=` / `name=`）原本按原文写进日志，与「只记长度」的声明不符；
  改为同样走 `Shape()`，只记长度。
- **反编译 / 解包方法论的风险披露**：`docs/无障碍补丁流水线.md` 的 P0 工具链与
  `docs/templates/无障碍可行性验证.md` 的复现命令各加一段提示 —— 这些操作**可能违反
  目标游戏的 EULA 或反规避条款**，技术上必需不等于法律上许可；`NOTICE.md` §6 新增中英
  双语说明。
- 「挂载点的唯一**合法**来源」改为「唯一**权威**来源」（`README.md` 与流水线两处）：
  原文意思是「实测出来的、不许猜」，但「合法」容易被读成法律判断。

### 六、第二轮审核（许可口径、脱敏与余额）

- **BepInEx 的版本对应关系写反了一处**：`NOTICE.md` 组件表把 `BepInEx 5.4.23.5`
  标成 LGPL-2.1。上游该 tag 的 `LICENSE` 是 MIT（`v5-lts` 线），LGPL-2.1 是 `master`
  的 v6。已改为两行分别标明 5.x = MIT、6.x = LGPL-2.1，并写清
  `licenses/MIT-BepInEx.txt` / `licenses/LGPL-2.1-BepInEx.txt` 各自对应哪个版本 ——
  这样才和 `README.md`、`docs/无障碍补丁流水线.md` 与三份范例的说法一致。
- `NOTICE.md` 的署名条款原用「均须」，与同一文件开头「不缩减 MIT」自相矛盾
  （MIT 不允许附加署名条件）。改为**请求**，并明写「不是附加条件、不得解释为限制
  MIT 已授予的权利」。
- 新增 [`docs/licenses.md`](docs/licenses.md)：`licenses/` 里 24 份许可证原文 + 1 份上游补丁片段 + 3 份通知
  范例的逐文件索引（组件、许可、版权）。索引放在 `docs/` 而非 `licenses/`，因为后者由
  组装脚本整份重建。
- `tools/zdsr_selftest/run.ps1` 与 `ZdsrSelfTest.csproj` 不再硬编码游戏目录：
  `-GameDir` / 环境变量 `A11Y_GAME_DIR`（直接构建 csproj 用 `/p:UnityManaged=…`
  或 `A11Y_UNITY_MANAGED`）；gcc 走 `-Gcc` / `A11Y_GCC` / PATH。
- `tools/zdsr_selftest/Program.cs` 的合成测试串不再用某个角色的名字（形态上像真台词），
  改成中性占位，断言内容不变。
- `templates/probe/Probe.csproj.template` 的 `NoWarn` 补 `CS0162`：
  `DumpUiText` 是 `const false`，包在 `if` 里的代码会被判定为不可达。
- 断言数口径统一：`README.md` 与 `CHANGELOG.md` 里的「64 条」标注为
  「0.2.0.0 时 64 条、0.2.1.0 增至 71 条」，当前总数以 71 条为准。
- **提交历史里的作者本机实验目录前缀已重写**：早期提交的模板/文档里带过作者本机的
  实验目录前缀，现已把重写时的全部提交（含两个 tag）里的该前缀统一换成 `D:\work\…`。
  历史里剩下的本机路径都是 `D:\work\…`、`D:\tools\w64devkit\…` 这类**不含用户名**的
  通用路径，按原样保留；当前树里只剩两处刻意保留的功能性字面量（组装脚本的映射源
  `D:\Steam\steamapps\common\钟塔 Belfry` 与争渡的默认安装路径），都是游戏/软件安装路径。
  全部提交的邮箱已是 GitHub noreply 地址。

> 本次修订**没有**改动平台层行为（`platform/` 只有注释变化）、契约层（`contract/`）。
> `licenses/` 只是把三份 `THIRD-PARTY-NOTICES.example-*.txt` 同步到姊妹仓当前版本
> （新增争渡 ZDSR 一项），其余许可证文本未动。也**没有**删掉三作的补丁点汇总表 ——
> 那些信息在三个公开姊妹仓里本来就有，删掉只会丢知识。

### 七、第二轮审核的复核补正（同日）

第一轮修订提交后，又按两条独立的对抗式审核意见做了补正 —— 都是「仓库自己写了、
一核就假」的那类句子，公开后一条 `git log -p` 就能推翻：

- **Tolk 的许可与构建事实**：原注释与文档称「Tolk 官方只有 MSVC 工程、不提供预编译
  二进制」，实测上游有 CI 构建的 `tolk.zip`（只有 `master` 分支、无版本 tag），
  且 `LICENSE.txt` 是 **LGPL-3.0**。`platform/Speech.cs`、`platform/Zdsr.cs` 的注释、
  `README.md`、`CHANGELOG.md`、`docs/无障碍补丁流水线.md`、`docs/licenses.md`、
  `NOTICE.md` 七处口径统一，并补上「随包分发须附许可全文、来源与修改说明」。
  `platform/` 的两处注释由 `tools/assemble_from_sources.py` 的 `_STALE_NOTES`
  在**输出**上更正（源仓库不动，重跑仍然逐字节一致；锚点对不上就直接报错）。
- **MIT 与「署名要求」的冲突**：`README.md` 许可节原写「附加的署名要求」「但须标注
  出处」，与 `NOTICE.md` 的「请求（而非强制）」及根 `LICENSE` 冲突。已统一为
  「MIT 唯一的强制义务是保留版权声明与许可全文；标注出处 / 注明已修改是请求」。
- **`docs/licenses.md` 的两处事实错误**：Capstone 不是 Tolk 的依赖（属 IL2CPP 工具链）；
  三份通知范例是「未取得书面许可」而非「责任自负」，且只有两份 Mono 范例是第 8 项、
  IL2CPP 那份是独立小节。`CHANGELOG.md` 的转述同步更正。
- **可机械核对的数字**：`README.md` 的骨架冒烟测试由「54 个文件」改为 **55 个**
  （27 个渲染文件 + `licenses/` 24 份许可证原文 + `.gitignore`/`.gitattributes` +
  `tools/compile_check.ps1` + `README.md`；三份姊妹作通知范例与上游补丁片段不再随骨架生成）。断言数 71 条（含 `Case_RegistryLookup`
  在争渡未安装时跳过一条）复核无误。
- **守卫脚本的路径**：`README.md` 与 `.gitignore` 原写 `build/check-staged.ps1`，
  实际只有 `build/check-staged.ps1.template`（由 `tools/new_game.py` 生成到
  新作的 `tools/check-staged.ps1`）。两处都已改正。
- **历史脱敏的口径收窄**：`filter-branch` 换掉的是作者本机的实验目录前缀（统一为
  `D:\work\…`）；历史里仍留着 `D:\work\…`、`D:\tools\w64devkit\…` 这类**不含用户名**的
  通用路径，按原样保留。原文写「本机工作目录已重写脱敏」过宽，已按事实收窄。
- **`platform/` 不再默认重生成**：0.2.0.0 起该目录有手工演进（`Repeat.cs`、争渡后端），
  再整份重建会删掉手工成果。组装脚本因此新增 `--refresh-platform`，默认只重写
  `licenses/`；`licenses/` 重跑后仍逐字节一致（已实测零 diff）。
- **游戏内专名**：`platform/UiNav.cs` 注释里的具体曲名与输入内容、`templates/game/TextProc.cs.template`
  里的角色名，都换成 `<曲名>` / `<已输入内容>` / `角色A` / `作品甲` 这类占位 ——
  模板会被 `new_game.py` 原样拷进新作，保留上一作的专名既无必要也不合适。
- **模板的性质写清楚**：`templates/game/UiNav.Game.cs.template` 与
  `templates/probe/ProbePlugin.cs.template` 里仍带上一作的类型名与成员，它们是
  **换作时的示例片段**，不是能直接编译的成品 —— README 的验证表下已加说明。

---

## 0.2.2.0 — 读不到文字时念什么、以及「激活」到底该不该立刻发生

用户反馈两个问题，它们其实是同一件事的两面：

> 1) 控件绑定的 Text 读不到时会直接念 GameObject 名 / 类型名 / ID，
>    而且**没有降级行为就执行激活**。
> 2) 本作导航模式快捷键要求是 **Ctrl+Alt**（组合键），不能和游戏自身热键冲突。

### 一、先修防御性正确性：IL2CPP 下 16 处 `as` / `is` / `GetType()` 判组件类型

这一条是**防御性正确性改动**，不是本次实机确认的故障：《不/存在的莉莉丝》实机
（Il2CppInterop 1.5.3）里 `GetComponent<RectTransform>()` 与 `transform is RectTransform`
都返回了正确结果，62 个 `Selectable` 全部扫到，**没有复现**「零控件 / 全念 Selectable /
读不到文字」。但 Il2CppInterop 的代理是**按「方法声明返回类型」造对象**的
（`s.transform` 的声明类型是 `Transform`），`as`/`is` 能不能过取决于具体版本与类型映射。
平台层不该把正确性押在代理实现上——所以 16 处统一改成原生类型判断
（`GetComponent<T>()`），语义不变、行为不变，只是不再依赖代理细节。

在会复现的运行时上（旧版 Il2CppInterop / 代理没做类型还原时），这些判定的表现是：

    s.transform is RectTransform     → 恒 false（哪怕底层真是 RectTransform）
    c as TextMeshProUGUI             → 恒 null
    s as Toggle / s is Button …      → 恒 null / 恒 false
    s.GetType().Name                 → 恒 "Selectable"（声明类型，不是原生类）

而且**全部静默**：不抛异常、不写日志 —— 界面明明有按钮却一个都扫不到、所有控件
都念 Selectable、文字一个都读不出来，全都不会留下线索。这正是不值得赌代理实现的原因。

统一改成 `GetComponent<T>()`（原生层判断类型），对象比较仍用 Unity 的 `==`：

| 原行 | 原写法 | 改为 |
|---|---|---|
| 321 | `s.transform is RectTransform`（Scan 第一道过滤器） | `s.GetComponent<RectTransform>() == null` |
| 466 | `c.transform as RectTransform`（GroupOf 的 Canvas 矩形） | `c.GetComponent<RectTransform>()` |
| 509 / 606 / 671 | `s.transform as RectTransform`（排序 / 可见性 / 行列） | `s.GetComponent<RectTransform>()` |
| 872 / 874 | `c as TextMeshProUGUI` / `c as Text`（文本唯一收口） | `c.GetComponent<TextMeshProUGUI>()` / `GetComponent<Text>()` |
| 1077-1079 | `s as Toggle` / `s as Slider` / `s as TMP_InputField`（Describe） | 三个 `GetComponent<T>()` |
| 1094-1095 | `s is Button` + `s.GetType().Name` | `ControlTypeName(s)`（真实类型的中文说法） |
| 1340 | 激活日志里的 `s.GetType().Name` | `ControlTypeName(s)`（日志也只给真实类型） |
| 1353 / 1365 / 1374 | `s as TMP_InputField` / `s as Toggle` / `s as Slider`（Activate） | 三个 `GetComponent<T>()` |
| 1381 | `s as Button`（Activate） | `s.GetComponent<Button>()` |
| 1436 | `s as Slider`（Adjust：左右键调滑条） | `s.GetComponent<Slider>()` |

纪律写进了 `UiNav.cs` 文件头：**平台层不许用 `as`/`is` 判 Unity 组件类型**，
也不引入 Il2CppInterop（契约层红线）。

同一轮 IL2CPP 实机编译还暴露了一处**跨运行时签名差异**：`EventSystem.RaycastAll`
的第二个参数在 Mono 版是 `System.Collections.Generic.List<RaycastResult>`，
在 Il2CppInterop 里是 `Il2CppSystem.Collections.Generic.List<RaycastResult>`
（传 System 的 List 直接 CS1503）。写死任何一边都会让另一边编不过，而引用
Il2CppInterop 又违反红线 —— 所以 `VisiblyClickable` 的射线改成
`RaycastAllCompat`（反射拿运行时的 MethodInfo、按**实际参数类型**造列表、
再按 `IEnumerable` / `Count`+`Item` 读回 `List<RaycastResult>`）。
拿不到结果时按「判不出遮挡」处理（不排除控件），绝不因为一次反射失败把整屏项漏掉；
MethodInfo 只查一次，且只有 `CfgVisibleOnly` 打开时才走这条路。

### 二、读不到文字：分层标签 + 结构化语义降级

旧 `TextOf` 的最后一行是 `return AncestorNameOf(s)`，而 `AncestorNameOf` 最后
`return s.gameObject.name` —— 这保证它**永远返回非空字符串**，调用方无法区分
「真标签」和「对象名」。对象名还经常长得像人话（`Exit` / `Load` / `Close`），
玩家会以为听到的就是那个按钮的名字。

现在标签和它的可信度一起返回（`LabelResult{Text, Quality, Source}`）：

| Quality | 来源 | 处理 |
|---|---|---|
| `Bound` | 控件子树文字 / 逐作 `GameLabelOf` | 照念 |
| `Nearby` | 别名表 / 同一行兄弟文字 / 输入框占位提示 | 照念 |
| `Semantic` | 以上全失败 | 念 **「未命名按钮，第 3 项，共 7 项，面板设置」** |
| `Raw` | 原始对象名（`AncestorNameOf`） | **默认不念**（`A11yHost.CfgSpeakRawName` 默认 false），原始名只进诊断日志 |

`TextOf` 保留为兼容包装（返回 `.Text`）；朗读一律走 `LabelText`。

顺带修了三处相关的退化：

- **占位文本要先判噪**：`OwnTextOf` 原来不过 `A11yHost.GameTextIsNoise` 就返回，
  导致预制体占位字（`New Text` / `Button`）被当成可读标签，`GameLabelOf` 那条逐作
  钩子永远轮不到被调用 —— 现在先过噪再判空。
- **不念英文对象名当组名**：`GroupName` 原来没钩子就念 Canvas 顶层祖先名
  （`Right` / `UpRight` / `Canvas`）。现在：钩子 → 名字含中日韩字符（照念）→
  `CfgSpeakRawName` 打开（照念）→ 中性兜底 **「面板 + 组号」**（`面板1` / `面板2`，
  多组时不至于全叫「面板」）。
- **不念本地化 key**：输入框标签 / 占位提示 / 当前内容像 `UI.Setting.Name` 这种
  内部 key 时跳过（保守判断：含 `.`/`_` 分隔、全可见 ASCII、无空格、至少两段；
  `Start` 这类真英文标签不会被误挡）。

### 三、降级确认：推断标签下的激活必须按两次

标签是推断出来的（`Semantic`，或 `Raw`）时，`UiNav.Update` 在退出确认之后、
`Activate` 之前插了一道状态机：

    第一次按回车/空格 → 重复朗读 + 「这一项读不出可读文字。再按一次确认；按别的键取消。」
    第二次按同一项   → 真正 Activate
    8 秒不按 / 换项 / 换组 / 退出导航 / 场景切换 → 自动清除

配置 `A11yHost.CfgUnknownConfirm`（默认 **true**，null 也按 true）。
退出确认**优先**：已武装退出确认时不再叠降级确认（否则退出要按三次回车）。
清理点覆盖 `ExitInternal`、`Announce`（方向键/换页/Home/End 都走它）、
`Update` 每帧的 `ValidateDegradedConfirm` 兜底。

### 四、导航开关：平台只收一个布尔，组合键留给逐作

平台层不再写死 Tab。新增**只增不改**钩子：

    internal static Func<bool> A11yHost.NavTogglePressed;

    // UiNav.Update
    navToggle = hook != null ? hook() : KeyEdge.Pressed(KeyCode.Tab);

钩子留空 = 前三作行为逐字节不变（Tab）。组合键放逐作层，因为：

- `Hotkey.cs` 的组合键语义要求**必须有主键**（`Ctrl+Alt` 单独写不成立，
  它同时会拒绝 `Ctrl+Alt+X` 这种「组合键 + 第三个键」误判为主键按下）；
- 边沿闩锁（`_navKeyLatched`，抬起复位）必须和「输入框聚焦时抢不抢键」放在一起；
- 配置项 `CfgNavKey` 由逐作 `Plugin.cs` 绑定，平台只收一个「这一帧要不要切」的布尔。

用户后来明确本作要**纯 `Ctrl+Alt`**（没有主键），所以平台层 `KeyEdge` 又补了
纯修饰键组合的判定（见下一节），逐作把 `CfgNavKey` 默认值改成 `Ctrl+Alt` 即可；
`Ctrl+Alt+G` 这类带主键的组合键仍走 `Hotkey`，两条路互不干扰
（`ModifierChordDown` 在按住期间出现其它键会作废，因此 `Ctrl+Alt+G` 不会误触发纯组合）。

另外 `KeyEdge.Pressed` 整段包了 `try/catch`：Active Input Handling 设成
Input System Package 时旧 `Input` 会抛 `InvalidOperationException`，异常冒到
`Plugin.Update` 会让热键整段失效并每帧刷日志。现在按「没按」处理，
与 `Hotkey.Down` 的纪律一致。UiNav 里的输入框提示也从「按 Tab 返回导航」
改成「再次按导航开关返回导航」（平台不知道逐作配的是哪个键）。

### 五、纯修饰键组合：`KeyEdge.ModifierChordDown`（0.2.2 新增）

`Hotkey` 表达不了「只有修饰键」的组合（它要求必须有主键），而用户要的正是纯
`Ctrl+Alt`。`KeyEdge` 新增一个跨作品通用的平台层 API，逐作直接调用：

    public static bool ModifierChordDown(string spec, float minHoldSeconds = 0.25f)

- `spec` 只允许修饰键，`+` 或空格分隔，大小写不敏感；认
  `Ctrl/Control`、`Alt`、`Shift`、`Win/Windows/Command/Cmd/Meta/Super`；
  组内左右键任意一个都算（Ctrl = `LeftControl` 或 `RightControl`）。
  出现任何非修饰键 token → 返回 **false**（带主键的组合键仍用 `Hotkey.Down`）。
- 语义：所有组同时按住 ≥ `minHoldSeconds`（默认 **0.25 秒**；负数/NaN 按 0）
  时返回 true **一次**；按住期间（武装那一帧之后）出现任何其它**键盘**键 →
  本次作废；触发或作废后必须**全部松开**才能再次触发（自带闩锁）。鼠标按钮不算「其它键」。
- 为什么记录「武装帧」而不是直接看 `Input.anyKeyDown`：按下修饰键那一帧
  `anyKeyDown` 必然为 true，直接判会立刻自我作废；所以只在
  `Time.frameCount > 武装帧` 之后再看到 `anyKeyDown` 才取消。
- 实现约束：只用 legacy `UnityEngine.Input` + `try/catch`（Input System-only 工程里
  旧 `Input` 会抛 `InvalidOperationException`，按「没按」处理并清状态）；
  用 `Time.unscaledTime`（暂停/降速时仍然可靠）；不引 `Il2CppInterop` / 游戏类型 /
  Input System；解析结果按 spec 缓存、状态全静态字段，**每帧不分配**；
  同一时刻只维护一组 chord（平台层只需要导航开关这一个）。
- `KeyEdge.Reset()` 一并清 chord 状态：场景切换 / 失焦后不会残留「已触发、等松手」。

逐作接法（用 `CfgNavKey`，本作默认值 `Ctrl+Alt`）：

    // Plugin.Awake
    A11yHost.NavTogglePressed = () => KeyEdge.ModifierChordDown(CfgNavKey.Value);

`ModifierChordDown` 已自带「触发后必须松手」的闩锁，这条路上不需要逐作再维护
`_navKeyLatched`；只有走 `Hotkey.Down`（修饰键+主键）时才需要逐作自己闩锁。

### 兼容性

- 平台层仍是零游戏类型依赖：`tools/compile_check.ps1` PASS，
  `.compilecheck` 临建工程 **0 警告 0 错误**（不引用 Assembly-CSharp）。
- 老作不绑新钩子/新配置时：导航开关仍是 Tab；`CfgSpeakRawName` 按 false、
  `CfgUnknownConfirm` 按 true（安全默认值）。**已发布的老作二进制不受影响**；
  若重新构建老作且希望保持旧朗读文本，需要显式把 `CfgSpeakRawName` 绑成 true。
- `A11yHost.Missing()` 不把 4 个新可选槽位算作缺失（避免老作启动白报几条，
  把真正该修的漏填项淹掉），`Clear()` 会一并清空。
- `KeyEdge.ModifierChordDown` / `Reset()` 的 chord 清理是**纯增量**：不调用它的作品
  完全不受影响，`Pressed` / `DigitPressed` / `Parse` 行为未变。
- 16 处 `as`/`is` 改动语义等价（换成 `GetComponent<T>()` 判原生类型），没有任何
  「行为变化」需要老作适配；它与 RaycastAllCompat 一起都属于**跨运行时兼容性**改动。

---

## 0.2.1.0 — 「找不到那个 dll」这件事：**先自动找，再随包兜底**

需求方原话：**「很多玩家找不到这个 dll，比如两年前的我」**。这句话把问题拆成了两半，
两半都要解决：

### 一、先自动找（治本）

争渡在注册表里登记了自己的安装位置 —— 这是本机实查的结果：

    HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\...
      DisplayName      = 争渡读屏
      InstallLocation  = C:\Program Files (x86)\zdsr\zdsr\

所以 `Zdsr.cs` 现在**先读注册表**（HKLM 两个视图 + HKCU，`DisplayName` 含「争渡」优先、
只含 `zdsr` 的排后面 —— 周边工具也会注册一个含 zdsr 的目录，但那里没有 ZDSRAPI.dll），
再回落到默认安装目录。**装在 D 盘、装在自定义目录的玩家从此不需要做任何事。**

顺序（与官方建议一致：安装目录那份跟着读屏一起升级）：

    注册表登记的安装目录 → 默认安装目录 → 插件目录（随包那份）→ 游戏目录

`A11Y_ZDSR_DIR` 仍然保留，且现在支持用 `;` 列多个目录。

**为什么用 advapi32 P/Invoke 而不是 `Microsoft.Win32.Registry`**：后者在 netstandard2.1
的引用集里是个转发类型，平台层一引用就得给每个工程加 NuGet 包（Mono / IL2CPP 两边都得管）。
本文件本来就是直接调 kernel32 的风格，保持一致 → 平台层依旧零额外依赖。

### 二、再随包兜底（治标），而且**带旧了也不会把玩家卡死**

发布包里现在带上一份 `ZDSRAPI_x64.dll` + `ZDSRAPI.dll`（放 `BepInEx\plugins\`；不带
`ZDSRAPI.ini`）。配套两条保障：

1. **安装目录那份永远优先** —— 包里这份只在机器上找不到安装目录时才被用到；
   玩家把包里这两个文件删掉，行为立刻回到「只读安装目录」。
2. **某一份报版本不匹配（`InitTTS` 返回 1）时，自动换下一份候选** —— 这条是为「包里那份
   随争渡升级而过期」准备的：安装目录的 dll 与读屏版本对不上时，兜底那份仍然够得着；
   反过来兜底那份过期时，也不会把玩家卡在「明明装了争渡却不出声」上。

打包脚本（各补丁仓库的 `build.ps1` / `release.ps1`）用同一套顺序找源目录，
拷贝时打印文件名/大小/SHA256；**构建机上没装争渡时只警告、不失败**（包里就没有兜底那份）。

> **分发口径**：争渡的 dll 只进发布包，**不进 git 仓库** —— 仓库里那句
> 「本仓库不含第三方二进制」仍然字面成立，而玩家拿到的包里是现成的。
> 致谢与许可说明写在包内文档里（未经修改、非商业随包分发，官方文档本身也告诉应用程序
> 把这些文件复制到自己目录）。

### 自检从 64 条涨到 71 条

新增：注册表查找能拿到真实安装目录、**第一份报版本不匹配时会换到第二份**、
所有候选都版本不匹配时给出可读原因（而不是判死）。桩 DLL 也多了第三种构建
（`InitTTS` 固定返回 1），专门用来造「包内那份太旧」这个场景。

---

## 0.2.0.0 — 争渡读屏后端 + 运行中切换后端：**一个「回来 0 但没出声」的接口**

### 为什么加这一级

平台层原有三级后端里**没有一级**能把话说给争渡读屏 —— 而争渡是国内使用最广的读屏：

| 后端 | 对争渡用户意味着什么 |
|---|---|
| Tolk | 要玩家自备 `Tolk.dll`（上游有 CI 构建的 `tolk.zip`，无版本 tag；LGPL-3.0，随包须附许可全文） |
| NVDA | 只喂 NVDA，争渡听不到 |
| SAPI | 能出声，但**不是玩家读屏的声音**：音色/语速/音量另一套，也不走读屏的排队 |

于是「只装争渡」的玩家一直听到的是另一个声音。新增 `platform/Zdsr.cs` 把官方 ZDSRAPI 接进来。

### 一条必须写进代码里的接口陷阱

官方文档写得很清楚，但很容易被忽略：

> `Speak()` 返回 **0 = 成功**；返回值 2 = 争渡没有运行或没有授权。

**未授权时 `Speak()` 照样返回 0** —— 那个 0 只说明消息送到了对端，与「读屏是否出声」无关。
所以可用性判据**不能**是 `Speak()` 的返回值，只能是 `GetSpeakState() ∈ {3,4}`
（3 = 正在朗读，4 = 空闲，两个都说明读屏活着且有授权）。商业版/青春版才有 API 权限，
公益档下 `GetSpeakState()` 恒为 2：这种情况下**如实判不可用**，让链子继续走 SAPI，
而不是让玩家面对一片安静还以为是自己没配好。

### 加载位置：**不随包分发 ZDSRAPI**

官方说明：应用程序可以直接调用争渡安装目录下的 dll，也建议这么做（争渡 26.6 更新过 dll，
自带旧版会踩版本不匹配）。所以候选顺序是 **争渡安装目录 → 插件目录 → 游戏目录**，
按进程位数选 `ZDSRAPI_x64.dll` / `ZDSRAPI.dll`；找不到 DLL 是**返回值**而不是异常
（用 `LoadLibraryExW` + `GetProcAddress`，`DllImport` 的编译期常量名表达不了「运行时选目录」）。
另留 `A11Y_ZDSR_DIR` 环境变量：设了就只找那一个目录（排查用，也让自检能把搜索范围钉死）。

### `platform/Hotkey.cs`：运行中切换后端

开着 NVDA 的玩家会想「听一下争渡」，而自动链会一直挑 NVDA —— 需要一个功能键。
配置项支持修饰键写法（`F9` / `Alt+Shift+F9` / `Ctrl+Alt+F9`），默认由逐作层定。

循环顺序 `自动 → Tolk → NVDA → 争渡 → SAPI → 自动`，**只停在当前可用的档位上**，
跳过谁就在播报里念出来。三条规则是被实测逼出来的：

1. **配置是「自动」时，循环起点按实际选中的后端算。** 否则第一下按下去切到的还是同一个
   （开着 NVDA 时自动挑中的就是 NVDA），玩家会以为键没生效。
2. **已经在「自动」上时，再切到「自动」是空转，跳过它继续往前找。** 否则
   「只有一个后端可用、而它正好是最后一档」时按键看起来是坏的。
3. 从**钉死**档位按下去时，「自动」仍是有效落点（= 取消钉死）。
4. 选中的档位**写回配置文件**（`ConfigEntry.Value` 赋值即落盘），下次启动仍是它。

### 机械自检（不需要真读屏）

`tools/zdsr_selftest/`：一个桩 ZDSRAPI DLL（`zdsr_stub.c`，把每次调用连同 UTF-16 文本原样记进日志，
返回值由环境变量控制）+ 一个直接编译 `platform/Zdsr.cs`、`platform/Hotkey.cs` 的控制台程序。

```
pwsh -NoProfile -File .\tools\zdsr_selftest\run.ps1     # 71 条断言
```

覆盖：DLL 缺失 / 未授权（**桩故意让 Speak 返回 0，断言我们仍判失败**）/ 可用 / 参数逐个回显
（含中文与全角标点、`InitTTS(0,NULL,false)`）/ 掉线恢复（含 5 秒门禁）/ 不刷屏 / Stop /
Braille 导出的新旧两种构建 / 按键描述解析（含 G3 那个「`TryParse("0")` 成功但得到 `KeyCode.None`」的坑）。

### 顺带修掉的两个「会静默吃掉新能力」的坑

- `tools/new_game.py` 的 L1 文件清单没加 `Zdsr.cs` / `Hotkey.cs` 的话，**新作骨架第一次编译就失败**
  （与当年漏 `KeyEdge.cs` 一模一样）。已加，并在注释里写明原因。
- `tools/assemble_from_sources.py` 会**先删掉 `platform\` 再按清单重建**。源仓库克隆一旦落后，
  跑一遍就会把 `Zdsr.cs`、`Hotkey.cs` 与 `Speech.CycleAvailable` 静默删掉（流水线 §1.3 的
  「平台层单向退化」，而且 `git status` 看起来还挺干净）。已加组装前断言：源仓库不含这两个文件
  就**拒绝运行**。

### 实测证据（本机，2026-10-15）

| 验证 | 怎么做的 | 结果 |
|---|---|---|
| 平台层编得过、无游戏类型依赖 | `tools/compile_check.ps1` | 0 错误 0 警告，`PASS` |
| 后端选路/失败路径/参数/按键解析 | `tools/zdsr_selftest/run.ps1` | **64 通过 0 失败** |
| 真读屏真的出声（阳性） | 宿主程序直接编译 `platform/Speech.cs`+`Zdsr.cs`，对着**真争渡**说一句，外部轮询 `GetSpeakState()` | 12/12 次采样为 **3（正在朗读）** |
| 同一句话不走争渡时争渡静默（阴性对照） | 同上，把后端钉成 SAPI | 12/12 次采样为 **4（空闲）** |
| 切换顺序（真环境：NVDA 在跑 + 争渡已授权） | 宿主程序调 `CycleAvailable()` 六次 | `争渡 → SAPI → 自动 → 争渡 → SAPI → 自动`，每次配置都跟着落盘；**从自动起第一下就到争渡** |
| 跳过路径 | 把 `A11Y_ZDSR_DIR` 指到空目录（争渡不可用）再跑 | `SAPI（已跳过 争渡）→ 自动 → SAPI（已跳过 争渡）…`，跳过理由念得出来 |
| 插件在游戏里跑 | 《钟塔》实机：装包 → 启动 → 按切换键 | 日志 `语音后端: NVDA` → 按键后 `语音后端: 争渡读屏（ZDSR），DLL=…，状态=空闲（可用）` + `[朗读] 语音后端：争渡读屏` |

### 尚未验证（诚实边界）

- **游戏内那一声是不是争渡念的**，没有硬证据：争渡作为读屏本身也在念东西，
  从进程外无法把某一句话归因到它。目前是「宿主集成测试证明这条通路真的出声」
  ＋「游戏内日志证明后端确实切到了争渡」，两段拼起来的结论。
- 修饰键写法只在解析层与宿主里验过，**没有在游戏里真按过** `Alt+Shift+F9`。
- 另外提醒：中文 Windows 上 **Alt+Shift 默认是切换输入法的热键**，
  嫌别扭就配 `Ctrl+Alt+F9`；修饰键必须完全一致（配 `F9` 时按住 Alt 不触发）。

---

## 0.1.1.0 — 重读缓冲区提升为 L1：**同一个坑踩了两次，这次用机械断言钉死**

### 两次事故

| 作 | 版本 | 现象 |
|---|---|---|
| 《钟塔》 | 0.1.0.1 | 复盘原文：「根因是**重读缓冲区**的覆盖面不全 …… **选项播报绕过了缓冲区**，所以停在选项上按退格什么也念不出来」 |
| 《妹控计划》 | 0.1.0.0 | **同款**：有选项时按退格念的是上一句台词。发布当天被玩家抓出、当天撤回重发（0.1.0.1） |

两次的根因是同一个：**缓冲区是逐作各写一份的**。
而「重读」的规则 —— 哪些内容该进、什么时候失效、重读路径能不能被去重吃掉 ——
**与具体游戏无关**。逐作各写一份，就一定会有人漏掉一条路径。

### 修法：把它变成平台层的事，再加一条机械断言

新增 `platform/Repeat.cs`（L1 冻结层），逐作层**只能往里塞**：

| 入口 | 语义 |
|---|---|
| `Repeat.Say(text, interrupt)` | 播报 **+** 进缓冲区 —— 逐作层所有朗读都该走这里 |
| `Repeat.Note(text)` | **只进缓冲区、不播报**（有配音的行、快进经过的行 —— 「只记不念」） |
| `Repeat.Push(text, tag)` | 临时优先项（选项列表）：进缓冲区 + 播报，且重读时**优先于台词** |
| `Repeat.Drop(tag)` | 撤销优先项（选完了 / 段落结束了），缓冲区**退回台词** |
| `Repeat.Again()` | 重读。**直接走 Speech，不去重、不排队** |

三条规则照抄两次复盘：

1. **凡是玩家可能想重听的东西都要进缓冲区** —— 包括有配音的行
   （补丁只是不自动念它，玩家主动按重读键仍然要能听到）。
2. **临时内容要能失效** —— 选项清掉之后不能再念那几个不存在的选项，
   所以 `Push`/`Drop` 成对出现，而不是覆盖主缓冲区。
3. **重读是玩家的主动请求** —— 直接播，否则「刚念完马上再听一遍」会被去重吃掉。

### 机械断言（这才是关键）

新增 `tools/lint_repeat.ps1`：**逐作层不许直接出现 `Speech.Speak(`**；
平台层只有 `Repeat.cs` 允许。已接进 `tools/compile_check.ps1` 的静态断言段，
由 `tools/new_game.py` 自动带进每一个新作。

`platform/UiNav.cs` 里原有 12 处直接播报，全部改走 `Repeat.Say` ——
顺带带来一个好处：**导航时的控件播报现在也能被重读键翻回来**。

> 教训：**复盘的结论如果只写在文档里，第三个作还会踩。**
> 能变成机械断言的，就不要只留成一句「请注意」。

### 顺带踩到的一个坑（编辑 .ps1 必须补回 BOM）

用工具改写 `compile_check.ps1` 之后文件丢了 UTF-8 BOM，PowerShell 5.1 按 GBK 解码，
整个脚本报「Missing closing '}'」加满屏乱码 —— 与流水线 §5.1 G5 记的是同一件事。
**任何自动改写 `.ps1` 的工具都要负责把 BOM 写回去**；
`tools/check-staged.ps1` 的「暂存的 .ps1 必须带 BOM」那条闸门正是拦这个的。

---

## 0.1.0.2 — `.gitignore` 的行内注释让 11 条规则全部失效

### 症状

《妹控计划》准备发布时，`git add -A` 把 `mod/package/`（BepInEx 的十几个第三方 DLL
与 `winhttp.dll`）和 `mod/dist/`（1 MB 发布 zip）一起暂存了。
`tools/check-staged.ps1` 拦了下来 —— 但**它是唯一拦住的东西**，`.gitignore` 本身一点作用都没起。

### 原因

规则写成了这样：

```
package/              # 组装出来的安装包，不是源码
dist/                 # 发布 zip（只进 GitHub Releases）
dl/                   # 下载的 BepInEx / NVDA zip
```

**gitignore 只在行首认 `#`。** 行内的 `#` 及其后面的内容属于**模式本身**，
于是这条规则实际是在找「一个叫 `package/` 后面跟一堆空格的目录」——
永远匹配不到任何东西，而且**不报错、不警告**。

验证（`git check-ignore -q <路径>`）：`extracted/`、`decompiled/`、`probe/evidence/*.png`、
`probe/evidence/*.log`、`dl/`、`bep_dl/`、`dist/`、`package/`、`.compilecheck/`、
`*.cfg`、`Interop/` —— **11 条全部为「未忽略」**。

### 影响面

- 本仓库：`.gitignore` 形同虚设（幸而实际入库的内容是干净的）。
- 三个已发布仓库：同样是这份模板，同样失效。实测只有 belfry 入了一个
  `probe/evidence/probe_full_dump.log` —— 那是**故意入库**的证据文件（只有类型与方法名），
  所以没造成实际损害。**但这是运气，不是设计。**
- 以后每一个新作：`tools/new_game.py` 会把这个文件拷进新仓库 —— 坑会一直传下去。

### 修法与纪律

1. 所有注释**另起一行**，规则行不再出现 `#`。
2. 文件头写明这条纪律，免得下次又有人图省事写行内注释。
3. 建议：`check-staged.ps1` 之外再加一条**反向自检** ——
   `git check-ignore` 逐条验证关键路径是否真被忽略（本次就是靠手工验才发现全失效的）。

> 教训：**「有这条规则」和「这条规则生效」是两件事。**
> 静默失效的配置比没有配置更危险 —— 前者会让人以为已经防住了。

---

## 0.1.0.1 — 第四作《妹控计划》逼出来的两件事：界面标签钩子，与两个骨架 bug

### 一、为什么要加钩子（不是「设计得更优雅」，是**原来那套真的不够用**）

《妹控计划》实机取证（`probe_scene_tree.txt` 844 行 + UiNav 自己的诊断转储）：

- **173 个「当前激活且可交互」的控件里，131 个读不到任何文字**，只能退化成对象名；
- 退化出来的名字分三类，一类比一类糟：
  1. **英文对象名**：`CommonCloseButton` / `Button (6)` / `CCPlus` / `VolumeButton` /
     `PlayMode` / `Pre` / `Next` —— 玩家原话：「setting、next 这种还好，其它就不一定了」；
  2. **预制体占位文字**：`New Text` / `Button` / `音效名称` / `000`
     —— 比对象名更糟：玩家会以为那东西真的叫「New Text」；
  3. **同名不同义**：`CommonButton` 在番茄钟里分别是「停止 / 暂停 / 下一个」，
     在互动区里是「和诗萌聊聊」。**只看对象名的平表永远区分不开**，必须看路径。

- 还有一个**顺序**问题：默认状态扫出 4 组，而最常用的功能条在**第 2 组**；
  进导航落在第 1 组（设置/装饰/收藏/换装/隐藏UI/退出），想去的地方就在隔壁，
  但要按 PageDown 才够得着 —— 而原来的播报只说「导航模式，第 1 组，共 6 项」，
  **连「一共 4 组」都不说**。玩家的原话是「顺序不对，找不到想去的地方」。

### 二、四个钩子（只增不改，不填即与从前逐字节一致）

| 钩子 | 语义 | 平台层的调用位置 |
|---|---|---|
| `GameTextIsNoise(string)` | 这段文字是预制体占位，别念 | `TextOn` 出口（所有文本读取的唯一收口） |
| `GameLabelOf(Selectable)` | 逐作标签解析 | `TextOf` 在「同行兄弟文字」之后、对象名兜底之前；`InputFieldLabel` 在占位提示之前 |
| `GameGroupName(Transform)` | 组的中文名 | `GroupName`（进组播报与总览） |
| `GameGroupPriority(Transform)` | 组排序权重，小的在前 | `Scan` 的组排序第一关键字 |

外加一条**独立的可用性修复**：进导航时报一次**全组总览**
（「第 1 / 4 组：功能条，6 项。全部 4 组：【功能条 6 项】；番茄钟 11 项；…。用 PageUp / PageDown 换组」），
换组时报「第 N / 共几组：组名，几项」。原来那条播报一个字都没提「还有别的组」。

### 三、顺手修掉的两个骨架 bug（都是「新作第一天就撞上」级别）

| bug | 症状 | 位置 |
|---|---|---|
| **`new_game.py` 漏拷 `platform/KeyEdge.cs`** | 新作骨架**第一次编译就失败**：`CS0103: 当前上下文中不存在名称"KeyEdge"`。UiNav.cs 的按键边沿检测直接引用它 | `tools/new_game.py` 的 L1 拷贝列表 |
| **csproj 模板注释里有连续两个减号** | MSBuild 报 `MSB4025: 未能加载项目文件。An XML comment cannot contain '-' '-'` —— 整个项目加载不了 | `templates/game/GameA11y.csproj.template` |

### 四、前三作是否受影响

**不受影响**：四个钩子默认全为 `null`，`Noise()` 原样返回、`GameLabelOf` 直接跳过、
`GroupPriority` 恒返回同一个值（排序结果与从前完全一致）、`GroupName` 退回根对象名。
唯一的**行为变化**是进组播报多了一句全组总览 —— 这一条是修 bug，不是改设计。

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
