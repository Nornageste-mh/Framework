# 附加条款与免责声明 / Additional Terms and Disclaimer

> **适用关系**：本文件是对仓库根目录 [`LICENSE`](LICENSE)（MIT 许可）的补充说明
> 与明确化，**不缩减** MIT 许可已授予的任何权利。若两者冲突，以 MIT 许可为准。
> 本文件由开源项目通用模板改写，**不构成法律意见**。

================================================================================
附加条款 / ADDITIONAL TERMS
================================================================================

1. 署名 / Attribution
---------------------

我们**请求**（而非强制）你在复制、修改或分发本软件时以显著方式标注：

  (a) 原始出处：https://github.com/Nornageste-mh/Framework.git，以及作者 Nornageste-mh；
  (b) 若发生修改，注明「已修改」及修改要点，不要让他人误以为修改版
      出自原作者或获得原作者背书。

以上是**请求，不是附加条件**：MIT 许可并不要求署名，任何人都可以按 MIT 的条款使用、
修改与再分发本软件 —— 本条不得被解释为对 MIT 已授予权利的限制。

We *request* (but do not require) that you credit the origin when you copy,
modify, or redistribute this software: this repository's URL and the author
Nornageste-mh. If you changed anything, please say so. This is a request, not a
condition: the MIT license does not require attribution, and nothing here
restricts the rights it grants.

2. 非官方声明 / Unofficial Project
----------------------------------

本软件是非官方的第三方无障碍辅助项目，与本软件所适配的游戏、软件、平台
及其开发商、发行商、版权方不存在任何隶属、合作、赞助、授权或背书关系。
相关商标、作品名称与内容的全部权利归各自权利人所有。

This is an unofficial, third-party accessibility project. It is not
affiliated with, authorized by, sponsored by, or endorsed by any game,
software, platform, developer, or publisher that it is designed to work with.
All trademarks and content remain the property of their respective owners.

3. 免责与责任限制 / Disclaimer and Limitation of Liability
----------------------------------------------------------

本软件按「现状」提供，不附带任何形式的明示或默示担保。在适用法律允许的
最大范围内，作者与贡献者对因使用或无法使用本软件而产生的任何直接、间接、
附带、特殊、惩罚性或后果性损害均不承担责任。这包括但不限于：

  (a) 游戏存档损坏、丢失或无法读取，游戏无法启动、崩溃或数据异常；
  (b) 游戏账号被限制、封禁，或游戏服务条款、最终用户许可协议被认定违反；
  (c) 与游戏开发商、发行商、平台运营方或任何第三方之间产生的争议、
      索赔、诉讼、禁令或任何形式的损失；
  (d) 设备损坏、系统故障、数据丢失或其他财产损失；
  (e) 第三方组件自身的许可瑕疵、权利主张或由此引发的任何责任。

是否使用本软件由你自行决定并自行承担全部风险。你应自行确认在当地法律及
相关服务条款下使用本软件是否合规。

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. TO THE
MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE AUTHORS AND CONTRIBUTORS
SHALL NOT BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
OR CONSEQUENTIAL DAMAGES ARISING FROM THE USE OF OR INABILITY TO USE THE
SOFTWARE. THIS INCLUDES, WITHOUT LIMITATION: SAVE DATA LOSS OR CORRUPTION;
GAME OR SOFTWARE FAILURE; ACCOUNT RESTRICTION OR BAN; ANY DISPUTE, CLAIM, OR
ACTION BY A GAME DEVELOPER, PUBLISHER, PLATFORM, OR OTHER THIRD PARTY; AND ANY
DEFECT IN THIRD-PARTY COMPONENTS. YOU USE THIS SOFTWARE AT YOUR OWN RISK.

4. 第三方组件 / Third-Party Components
--------------------------------------

本软件可能包含或依赖第三方代码。该部分不受本许可授权，其版权与许可归
各自权利人所有，并适用其各自的许可条款。分发时须保留其原始版权声明与
许可文本。

This software may include or depend on third-party code, which is licensed
under its own terms and is not covered by this license. Their copyright
notices and license texts must be preserved.

5. 本仓库第三方组件明细 / Third-Party Components in This Repository
-------------------------------------------------------------------

下表为本仓库实际涉及或依赖的第三方组件，**不受本 MIT 许可授权**，适用其各自许可：

| 组件 | 许可 | 权利人 | 说明 |
|---|---|---|---|
| BepInEx 5.x（含 5.4.23.5，`v5-lts` 分支） | MIT | BepInEx 项目（Bepis） | **5.x 是 MIT**；文本见 `licenses/MIT-BepInEx.txt`。本仓库不随附其二进制 |
| BepInEx 6.x（`master` 分支） | LGPL-2.1 | BepInEx Team | **6.x 才是 LGPL-2.1**；文本见 `licenses/LGPL-2.1-BepInEx.txt`。逐作发布时按该作实际用的版本附对应文本 |
| HarmonyX | MIT | BepInEx 项目 | 文本见 `licenses/MIT-HarmonyX.txt`（上游 Harmony 2 另有 `MIT-Harmony.txt`） |
| UnityDoorstop | LGPL-2.1 | NeighTools（组织；上游 `LICENSE` 无版权行，权利人无法逐字核实） | 文本见 `licenses/LGPL-2.1-UnityDoorstop.txt` |
| NVDA Controller Client | LGPL-2.1 | NV Access | 本仓库不随附；由使用方自行取得 |
| Tolk（可选） | LGPL-3.0 | 上游 `dkager/tolk`（Davy Kager 等）；`ndarilek/tolk` 是持续维护的 fork | 上游 `LICENSE.txt` 为 LGPL-3.0；官方有 CI 构建的 `tolk.zip`（无版本 tag）。本仓库不随附；若随包分发 Tolk 本体，须按 LGPL-3.0 附许可证全文、来源与修改说明。其官方 `tolk.zip` 里另带 NVDA Controller Client（LGPL-2.1，须一并保留包内的 `LICENSE-NVDA.txt`）与 `SAAPI64.dll` / `dolapi32.dll` 等第三方专有组件（包内无许可文本，随包前须自行确认，建议改为让玩家自备） |
| 争渡读屏 ZDSRAPI（可选） | **专有软件**（非开源） | 争渡读屏（ZDSR）的作者 / 发行方 | 本仓库**不随附**其 DLL；发布包若放兜底副本，须自行取得授权并自负责任；本项目未取得其书面许可 |

分发本软件时，须保留上述组件的原始版权声明与许可文本。若你重新分发本项目的
构建产物，请自行确认已满足全部第三方许可的署名、附随与源码提供要求。

`licenses/` 里还收录了文档提到的**分析 / 构建工具链**的许可证文本（Mono.Cecil、MonoMod、
Il2CppInterop（LGPL-3.0）、Cpp2IL、AsmResolver、AssetRipper.*、Capstone.NET、Capstone
（BSD-3-Clause）、Disarm、Iced、SemanticVersioning、uTinyRipper、Dobby（Apache-2.0）、
.NET runtime 等）。这些工具只在本机制作补丁时使用，**本仓库不随附它们的二进制**；
逐文件对应关系见 [`docs/licenses.md`](docs/licenses.md)。

6. 关于反编译与资源解包 / On Decompilation and Asset Extraction
--------------------------------------------------------------

本仓库的部分文档（`docs/`）为了说明互操作补丁点，描述了反编译、资源解包与脚本
提取的方法。此类行为**可能违反目标软件的最终用户许可协议（EULA）或反规避条款**，
其合法性因司法辖区而异。文档给出这些步骤只为技术说明，不构成对合法性的保证；
使用者须自行评估并承担全部风险。任何提取产物都不得提交进本仓库、不得随补丁分发。

Some documents in this repository describe decompilation and asset extraction
for interoperability purposes. Such acts may violate the target software's
EULA or anti-circumvention terms. They are described for technical reference
only, without any warranty of legality; you are responsible for assessing the
risk yourself. Extracted content must never be committed or redistributed.

The components above are licensed under their own terms and are **not** covered
by this MIT license. Preserve their copyright notices and license texts when
redistributing.
