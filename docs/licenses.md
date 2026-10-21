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
| `LGPL-2.1-BepInEx.txt` | BepInEx 6.x（`master` / v6） | LGPL-2.1 | BepInEx Team |
| `MIT-BepInEx.Harmony.txt` | BepInEx.Harmony | MIT | BepInEx 项目 |
| `MIT-HarmonyX.txt` | HarmonyX | MIT | Copyright (c) 2020 BepInEx |
| `MIT-HarmonyX-AndreasPardeike.txt` | HarmonyX 的上游（Harmony 2） | MIT | Copyright (c) 2017 Andreas Pardeike |
| `MIT-Harmony.txt` | Harmony（旧版） | MIT | Copyright (c) 2017 Andreas Pardeike |
| `LGPL-2.1-UnityDoorstop.txt` | UnityDoorstop（`winhttp.dll`） | LGPL-2.1 | Neighhiola |
| `LGPL-2.1-NVDA-ControllerClient.txt` | NVDA Controller Client | LGPL-2.1 | NV Access |
| `LGPL-2.1.txt` | LGPL-2.1 标准全文（与 NVDA 版逐字节相同） | LGPL-2.1 | Free Software Foundation |
| `BSD-3-Clause-Capstone.txt` | Capstone 反汇编框架（Tolk 的依赖） | BSD-3-Clause | Nguyen Anh Quynh / COSEINC |
| `MIT-Capstone.NET.txt` | Capstone.NET 绑定 | MIT | Ahmed Garhy |
| `LGPL-3.0-Il2CppInterop.txt` | Il2CppInterop | **LGPL-3.0** | BepInEx 项目 |
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
| `Apache-2.0-Dobby.txt` | Dobby（UnityDoorstop 的依赖） | Apache-2.0 | jmpews |

> - 上表是**文本**清单，不等于发布包必须包含的组件清单；逐作发布时按该作实际随包的
>   二进制重新列一遍（范例见下）。
> - **Tolk** 是可选依赖（要玩家自备 `Tolk.dll`，官方不提供预编译二进制），**本仓库
>   不随附**，因此这里没有它的文本；用到时请从 Tolk 发行包取。上游许可是
>   **LGPL-3.0**（`ndarilek/tolk` 的 `LICENSE.txt`），不是 BSD —— 若随包分发，
>   须按 LGPL-3.0 履行相应义务。
> - **争渡读屏的 `ZDSRAPI.dll` / `ZDSRAPI_x64.dll` 是专有软件**（非开源、本项目未取得
>   书面许可、本仓库不随附）。若你在发布包里放兜底副本，请先自行取得授权 ——
>   见根目录 [`NOTICE.md`](../NOTICE.md) 第 5 节。

## 通知范例

`THIRD-PARTY-NOTICES.example-*.txt` 是三个姊妹仓发布包里实际使用的
`THIRD-PARTY-NOTICES.txt`，原样收录供参考：

| 文件 | 对应补丁 | 引擎路线 | 说明 |
|---|---|---|---|
| `THIRD-PARTY-NOTICES.example-belfry-mono.txt` | BelfryForAccessibility | Mono | 含 NVDA Controller Client、BepInEx 5 |
| `THIRD-PARTY-NOTICES.example-noexistence-il2cpp.txt` | TheNOexistenceNForAccessibility | IL2CPP | 含 Il2CppInterop、BepInEx 6、Cpp2IL |
| `THIRD-PARTY-NOTICES.example-transparenther-mono.txt` | TransparentHerForAccessibility | Mono | 含 NVDA Controller Client、BepInEx 5 |

三份范例的组件与版本各不相同，**逐作发布时必须重写**，不要直接抄；每份第 8 项
都单列了争渡 ZDSRAPI（专有、非开源、须自行取得授权）。
