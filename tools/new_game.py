# -*- coding: utf-8 -*-
r"""从 A11yFramework 生成一个新作的骨架。

把「复制—改名—局部改写」这件事变成一条命令，并且保证：
  · 平台层整份拷贝、只换 namespace（不再手工改名）
  · 逐作文件从模板生成，占位符一次替换完
  · .ps1 保持 UTF-8 **带 BOM**（否则 PowerShell 5.1 按 GBK 解码 → 语法错误）
  · .cs 保持无 BOM 的 UTF-8

用法：
    python tools/new_game.py --ns MyGameA11y --game MyGame --exe MyGame.exe ^
        --guid mygame.a11y.reader --title 《我的游戏》 --route mono --out D:\work\MyGameA11y
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # A11yFramework 仓库根

PLACEHOLDER_FILES = [
    ("templates/game/Plugin.cs.template",        "mod/src/{ns}/Plugin.cs",            True),
    ("templates/game/TextProc.cs.template",      "mod/src/{ns}/TextProc.cs",          True),
    ("templates/game/UiNav.Game.cs.template",    "mod/src/{ns}/UiNav.Game.cs",        True),
    ("templates/game/GameA11y.csproj.template",  "mod/src/{ns}/{ns}.csproj",          True),
    ("build/build.ps1.template",                 "mod/build.ps1",                     False),
    ("build/release.ps1.template",               "mod/release.ps1",                   False),
    ("build/makezip.ps1.template",               "mod/tools/makezip.ps1",             False),
    ("build/check-staged.ps1.template",          "tools/check-staged.ps1",            False),
    ("probe/run_probe.ps1.template",             "probe/run_probe.ps1",               False),
    ("probe/screenshot.ps1.template",            "probe/screenshot.ps1",              False),
    ("templates/probe/ProbePlugin.cs.template",  "probe/plugin/ProbePlugin.cs",       True),
    ("templates/probe/Probe.csproj.template",    "probe/plugin/{ns}Probe.csproj",     False),
]

DOC_FILES = [
    ("docs/templates/无障碍可行性验证.md", "无障碍可行性验证.md"),
    ("docs/templates/测试问卷.md",         "测试问卷.md"),
    ("docs/templates/安装说明.md",         "mod/package/安装说明.md"),
    ("docs/templates/常见问题.md",         "mod/package/常见问题.md"),
    ("docs/无障碍补丁流水线.md",           "docs/无障碍补丁流水线.md"),
]


def read(p):
    with open(p, "rb") as f:
        raw = f.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    if bom:
        raw = raw[3:]
    return raw.decode("utf-8"), bom


def write(p, text, bom):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    data = text.encode("utf-8")
    with open(p, "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + data)


def apply_route(text, route):
    """按 @@ROUTE:xxx@@ / @@ENDROUTE@@ 标记裁掉不属于本路线的内容（连同标记行）。"""
    out, mode = [], None          # mode: None | 'keep' | 'drop'
    for line in text.split("\n"):
        if "@@ROUTE:" in line:
            r = line.split("@@ROUTE:", 1)[1].split("@@", 1)[0]
            mode = "keep" if r == route else "drop"
            continue
        if "@@ENDROUTE@@" in line:
            mode = None
            continue
        if mode == "drop":
            continue
        out.append(line)
    return "\n".join(out)


def substitute(text, subs):
    for k, v in subs.items():
        text = text.replace(k, v)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", required=True, help="C# namespace / 程序集名，例如 BelfryA11y")
    ap.add_argument("--game", required=True, help="MSBuild 属性前缀，例如 Belfry（-> BelfryGameDir）")
    ap.add_argument("--exe", required=True, help="游戏可执行文件名，例如 The Belfry.exe")
    ap.add_argument("--guid", required=True, help="BepInEx 插件 GUID")
    ap.add_argument("--title", required=True, help="游戏中文名，例如 《钟塔》")
    ap.add_argument("--route", required=True, choices=["mono", "il2cpp"])
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--version", default="0.1.0.0", help="纯数字四段版本号")
    ap.add_argument("--display", default=None, help="BepInEx 显示名，默认由 --title 推")
    ap.add_argument("--datadir", default=None, help="<Game>_Data 目录名，默认按 --exe 推")
    ap.add_argument("--gamedir", default=r"D:\Steam\steamapps\common\<游戏目录>")
    a = ap.parse_args()

    if not os.path.isdir(os.path.join(ROOT, "platform")):
        sys.exit("请在 A11yFramework 仓库根目录下运行（找不到 platform/）")

    # 版本号守卫（流水线 G7）：含字母会被 BepInEx 静默跳过整个插件
    parts = a.version.split(".")
    if not (len(parts) in (2, 3, 4) and all(p.isdigit() for p in parts)):
        sys.exit("版本号必须是纯数字分段（例如 0.1.0.1）；含字母会让 BepInEx 静默跳过整个插件")

    display = a.display or (a.title.strip("《》") + " A11y Reader")
    procname = os.path.splitext(a.exe)[0]      # 进程名：探针脚本用它找游戏进程
    datadir = a.datadir or (procname + "_Data")
    out = os.path.abspath(a.out)
    if os.path.isdir(out) and os.listdir(out):
        sys.exit("输出目录非空，拒绝覆盖: " + out)

    subs = {
        "{{NS}}": a.ns,
        "{{GAME}}": a.game,
        "{{EXE}}": a.exe,
        "{{GUID}}": a.guid,
        "{{TITLE}}": a.title.strip("《》"),
        "{{DISPLAY}}": display,
        "{{VERSION}}": a.version,
        "{{DATADIR}}": datadir,
        "{{PROCNAME}}": procname,
        "{{GAMEDIR}}": a.gamedir,
    }

    made = []

    # ---- L1 平台层：整份拷贝，只换 namespace ----
    # ⚠ KeyEdge.cs 也属于 L1：UiNav.cs 里的按键边沿检测直接引用它。
    #   0.1.0.0 的列表漏了它，导致新作骨架**第一次编译就失败**
    #   （CS0103: 当前上下文中不存在名称"KeyEdge"）。0.1.0.1 补上。
    for fn in ("Speech.cs", "Nvda.cs", "Sapi.cs", "UiNav.cs", "KeyEdge.cs"):
        text, _ = read(os.path.join(ROOT, "platform", fn))
        text = text.replace("namespace A11yFramework", "namespace " + a.ns)
        if "namespace " + a.ns not in text:
            sys.exit("%s 里没有找到 namespace A11yFramework，平台层可能被改过" % fn)
        dst = os.path.join(out, "mod", "src", a.ns, fn)
        write(dst, text, False)
        made.append(dst)

    # ---- L2 契约层 ----
    text, _ = read(os.path.join(ROOT, "contract", "A11yHost.cs"))
    write(os.path.join(out, "mod", "src", a.ns, "A11yHost.cs"),
          text.replace("namespace A11yFramework", "namespace " + a.ns), False)
    made.append(os.path.join(out, "mod", "src", a.ns, "A11yHost.cs"))

    # ---- 模板文件 ----
    for src_rel, dst_rel, is_cs in PLACEHOLDER_FILES:
        src = os.path.join(ROOT, src_rel.replace("/", os.sep))
        text, bom = read(src)
        text = apply_route(text, a.route)
        text = substitute(text, subs)
        dst = os.path.join(out, dst_rel.format(ns=a.ns).replace("/", os.sep))
        # .cs 一律无 BOM；.ps1 保持原样（带 BOM）
        write(dst, text, False if is_cs else bom)
        made.append(dst)

    # ---- 文档骨架 ----
    for src_rel, dst_rel in DOC_FILES:
        src = os.path.join(ROOT, src_rel.replace("/", os.sep))
        text, bom = read(src)
        write(os.path.join(out, dst_rel.replace("/", os.sep)),
              substitute(text, subs), bom)
        made.append(os.path.join(out, dst_rel.replace("/", os.sep)))

    # ---- 许可证 ----
    lic_src = os.path.join(ROOT, "licenses")
    lic_dst = os.path.join(out, "mod", "licenses")
    os.makedirs(lic_dst, exist_ok=True)
    for fn in sorted(os.listdir(lic_src)):
        sp = os.path.join(lic_src, fn)
        if os.path.isfile(sp):
            shutil.copy2(sp, os.path.join(lic_dst, fn))

    # ---- 根文件 ----
    for fn in (".gitignore", ".gitattributes"):
        sp = os.path.join(ROOT, fn)
        if os.path.isfile(sp):
            shutil.copy2(sp, os.path.join(out, fn))

    # compile_check.ps1 借一个本机已安装的游戏来取 UnityEngine / BepInEx 引用。
    # 生成新作时把它的默认 -GameDir 换成新作自己的目录。
    # 注意保留 BOM —— 它是 .ps1，PS 5.1 读无 BOM 的中文脚本会直接语法错误。
    cc_text, cc_bom = read(os.path.join(ROOT, "tools", "compile_check.ps1"))
    cc_text = cc_text.replace(r"D:\Steam\steamapps\common\钟塔 Belfry", a.gamedir)
    write(os.path.join(out, "tools", "compile_check.ps1"), cc_text, True)

    # README 骨架（流水线 §6 P7 的节名，逐作填内容）
    readme = os.path.join(out, "README.md")
    if not os.path.exists(readme):
        write(readme, README_SKELETON.format(
            ns=a.ns, title=a.title.strip("《》"), guid=a.guid, route=a.route), False)

    print("已生成 %d 个文件 -> %s" % (len(made), out))
    print()
    print("下一步（按这个顺序）：")
    print("  1. 填 mod/src/%s/UiNav.Game.cs  —— 别名表与姓名框探测，**每一条都要有依据**" % a.ns)
    print("  2. 填 mod/src/%s/TextProc.cs    —— 先用 P0 导出的剧本表离线跑规则" % a.ns)
    print("  3. 填 mod/src/%s/Plugin.cs      —— 配置项里的实测数字与补丁点（反编译实查）" % a.ns)
    print("  4. 填 mod/src/%s/UiNav.Game.cs、probe/、README.md" % a.ns)
    print("  5. cd mod; .\\build.ps1 -GameDir <游戏目录>")
    print()
    print("平台层（Speech/Nvda/Sapi/UiNav.cs）**不要再改** —— 改了就不再是冻结层。")


README_SKELETON = """# {ns}

> 《{title}》的读屏无障碍补丁。
> 平台层与契约层来自 [A11yFramework](https://github.com/Nornageste-mh/Framework)。

## 说明

TODO 这个补丁做了什么、覆盖哪些内容、明确**不做什么**。

## 安装（仅限正版玩家）

TODO 见 mod/package/安装说明.md。

## 主要快捷键

| 快捷键 | 功能 |
|---|---|
| @@B@@1@@B@@-@@B@@9@@B@@ | 选择对应编号的选项 |
| @@B@@0@@B@@ | 限时选择里「立刻沉默」 |
| @@B@@Backspace@@B@@ | 重读最近朗读过的一段 |
| @@B@@Tab@@B@@ | 进入 / 退出界面导航模式 |
| @@B@@↑@@B@@ @@B@@↓@@B@@ | 上一项 / 下一项 |
| @@B@@←@@B@@ @@B@@→@@B@@ | 调整滑条 |
| @@B@@回车@@B@@ / @@B@@空格@@B@@ | 导航模式下激活控件；否则交给游戏推进剧情 |
| @@B@@Home@@B@@ / @@B@@End@@B@@ | 第一项 / 最后一项 |
| @@B@@PageUp@@B@@ / @@B@@PageDown@@B@@ | 切换面板组 |

**游戏原生占用的键**（模组不会去抢，也不要拿来当重读键）：TODO 反编译实查后填写。

## 已知问题 / 注意事项

TODO

## 构建

@@F@@powershell
cd mod
.\\build.ps1 -GameDir "<游戏目录>"
@@F@@

### 目录结构

TODO

### 模组做了什么

| 功能 | 挂载点 |
|---|---|
| TODO | TODO |

### 几条踩过的坑（改之前请先读）

TODO ★ 逐作积累，这一节最有价值。至少写下你在本作上真正踩到的坑。

## 如何复现分析

TODO

## 合规说明

TODO 见 A11yFramework 的 README「IP 与合规」。

## 许可

TODO
""".replace("@@B@@", chr(96)).replace("@@F@@", chr(96) * 3)


if __name__ == "__main__":
    main()
