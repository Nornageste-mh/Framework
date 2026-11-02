# `licenses/` 索引 / License Text Index

`licenses/` 目录只放**第三方的许可证原文、通知范例与补丁文本**，不受本仓库根目录
[`LICENSE`](../LICENSE)（MIT）授权 —— 版权归各自权利人，适用各自条款。

> 本索引放在 `docs/` 而不是 `licenses/` 下：`licenses/` 由
> `tools/assemble_from_sources.py` 整份重建（先 `rmtree` 再拷），里面不能放手写文件，
> 否则重跑会把索引删掉。

**本仓库不随附任何第三方二进制**。这里收录文本，是为了逐作发布补丁包时能直接把
需要的许可文本抄进发布包 —— BepInEx 官方 zip 里一个许可文件都不带，
NVDA Controller Client、UnityDoorstop 等也不带。

## 许可证原文

| 文件 | 组件 | 许可 | 版权 / 出处 |
|---|---|---|---|
| `MIT-BepInEx.txt` | BepInEx 5.x（`v5-lts` 分支，含 5.4.23.5） | MIT | Copyright (c) 2018 Bepis |
| `LGPL-2.1-BepInEx.txt` | BepInEx 6.x（`master` 分支） | LGPL-2.1 | BepInEx Team |
| `MIT-BepInEx.Harmony.txt` | BepInEx.Harmony | MIT | BepInEx 项目（上游版权行为 `Copyright (c) 2019 `，年份在、权利人留空，按原样保留） |
| `MIT-HarmonyX.txt` | HarmonyX | MIT | Copyright (c) 2020 BepInEx |
| `MIT-HarmonyX-AndreasPardeike.txt` | HarmonyX 的上游（Harmony 2） | MIT | Copyright (c) 2017 Andreas Pardeike |
| `MIT-Harmony.txt` | Harmony（旧版） | MIT | Copyright (c) 2017 Andreas Pardeike |
| `LGPL-2.1-UnityDoorstop.txt` | UnityDoorstop（`winhttp.dll`） | LGPL-2.1 | NeighTools（组织；上游 `LICENSE` 无版权行，权利人无法逐字核实） |
| `LGPL-2.1-NVDA-ControllerClient.txt` | NVDA Controller Client | LGPL-2.1 | NV Access |
| `LGPL-2.1.txt` | LGPL-2.1 标准全文（与 NVDA 版逐字节相同） | LGPL-2.1 | Free Software Foundation |
| `BSD-3-Clause-Capstone.txt` | Capstone 反汇编框架（IL2CPP 解包/分析工具链的依赖，**与 Tolk 无关**；本仓库不随附其二进制） | BSD-3-Clause | Nguyen Anh Quynh / COSEINC |
| `MIT-Capstone.NET.txt` | Capstone.NET 绑定 | MIT | Ahmed Garhy |
| `LGPL-3.0-Il2CppInterop.txt` | Il2CppInterop | **LGPL-3.0** | BepInEx 项目（knah 及 Il2CppInterop 贡献者） |
| `il2cppinterop-pr277.patch` | Il2CppInterop 上游未合并 PR #277（+7 行）的完整改动 | LGPL-3.0 | Alec Hall |
| `MIT-Mono.Cecil.txt` | Mono.Cecil | MIT | Jb Evain / Novell |
| `MIT-MonoMod.txt` | MonoMod | MIT | 0x0ade |
| `MIT-Cpp2IL.txt` | Cpp2IL | MIT | Sam Byass |
| `MIT-AsmResolver.md` | AsmResolver | MIT | Washi |
| `MIT-AssetRipper.CIL.txt` | AssetRipper.CIL | MIT | ds5678 |
| `MIT-AssetRipper.Primitives.md` | AssetRipper.Primitives | MIT | ds5678 |
| `MIT-Disarm.txt` | Disarm | MIT | Sam Byass |
| `MIT-Iced.txt` | Iced | MIT | iced 项目 |
| `MIT-SemanticVersioning.txt` | SemanticVersioning | MIT | Adam Reeve |
| `MIT-uTinyRipper.md` | uTinyRipper | MIT | mafaca |
| `MIT-dotnet-runtime.txt` | .NET runtime | MIT | .NET Foundation |
| `Apache-2.0-Dobby.txt` | Dobby（BepInEx 6 / IL2CPP 运行时的依赖） | Apache-2.0 | jmpews |

> - `licenses/` 共 28 个文件：**24 份许可证原文** + **3 份通知范例** + 1 份上游补丁片段
>   （`il2cppinterop-pr277.patch`，不是许可证文本）。
> - 上表是**文本**清单，不等于发布包必须包含的组件清单；逐作发布时按该作实际随包的
>   二进制重新列一遍（范例见下）。`tools/new_game.py` 生成骨架时已按路线只拷贝
>   实际随包组件的文本（Mono 4 份 / IL2CPP 5 份），不再整目录拷贝；路线白名单在
>   `new_game.py` 的 `ROUTE_LICENSE_FILES`，新增组件时要同步。
> - **Tolk** 是可选依赖（玩家自备 `Tolk.dll`）。上游是 `dkager/tolk`（Davy Kager 等），
>   持续维护的 fork 是 `ndarilek/tolk`；后者的 releases 有 CI 构建的 `tolk.zip`，
>   但只有 `master` 分支、没有版本 tag（引用时写提交号）。上游许可是 **LGPL-3.0**
>   （`ndarilek/tolk` 的 `LICENSE.txt`）。
>   **本仓库不随附**，因此这里没有单列它的文本 —— LGPL-3.0 用的是同一份标准文本，
>   随包时可用 `LGPL-3.0-Il2CppInterop.txt` 一份代替，并自行补上来源与修改说明。
> - **争渡读屏的 `ZDSRAPI.dll` / `ZDSRAPI_x64.dll` 是专有软件**（非开源、本项目未取得
>   书面许可、本仓库不随附）。若你在发布包里放兜底副本，请先自行取得授权 ——
>   见根目录 [`NOTICE.md`](../NOTICE.md) 第 5 节。

## 跨引擎作品的许可边界（0.2.6.0 补注）

第 8–10 作不是 Unity（KiriKiri Z / Ren'Py / NVDA 双进程），本仓库**不收录、也不分发**
它们的任何二进制或引擎文件：

- **KiriKiri Z 作**：补丁是 C++ `a11y.dll` + 改归档注入器，引擎本体（`krkrz`）是游戏自带、
  不随补丁分发；Tolk 同为可选依赖（LGPL-3.0，本仓库不随附）、NVDA Controller Client
  LGPL-2.1、争渡 ZDSR 专有 —— 规则与 Unity 路线相同。
- **Ren'Py 作**：补丁是松散 `.rpy` 文本，**不含 Ren'Py 引擎**（引擎由游戏自带）；
  NVDA Controller Client 随包时按 LGPL-2.1 附文本。争渡 DLL 只进包不入库，且不带
  `ZDSRAPI.ini`。
- **NVDA 双进程作**：仓库自身没有 LICENSE，本框架**不采纳其路线**，也不复制其代码；
  只吸收测试方法学（流水线 §5.7）。

> 结论不变：`licenses/` 仍然只服务 Unity 平台层；跨引擎作品的随包组件由**各自仓库**
> 按实际清单列明，不要把它们的许可文本混进本仓库的路线白名单。

## 通知范例

`THIRD-PARTY-NOTICES.example-*.txt` 是三个姊妹仓发布包里实际使用的
`THIRD-PARTY-NOTICES.txt`，原样收录供参考（**原样收录，不含背书**）：

| 文件 | 对应补丁 | 引擎路线 | 说明 |
|---|---|---|---|
| `THIRD-PARTY-NOTICES.example-belfry-mono.txt` | BelfryForAccessibility | Mono | 含 NVDA Controller Client、BepInEx 5 |
| `THIRD-PARTY-NOTICES.example-noexistence-il2cpp.txt` | TheNOexistenceNForAccessibility | IL2CPP | 含 Il2CppInterop、BepInEx 6、Cpp2IL |
| `THIRD-PARTY-NOTICES.example-transparenther-mono.txt` | TransparentHerForAccessibility | Mono | 含 NVDA Controller Client、BepInEx 5 |

`tools/new_game.py` 生成骨架时**只拷上面 24 份许可证原文**（不含三份范例与 `il2cppinterop-pr277.patch`），因为范例是别的作品的通知文本。

三份范例的组件与版本各不相同，**逐作发布时必须重写**，不要直接抄；三份都单列了
争渡 ZDSRAPI（专有、非开源、**未取得书面许可**；两份 Mono 范例是第 8 项，IL2CPP 那份
是独立小节）。范例里给出的再分发依据来自争渡官方 API 文档，属姊妹仓各自的分发决定，**不代表本框架的建议**；本框架不随附
该 DLL，随包与否请自行取得授权并自负责任。
