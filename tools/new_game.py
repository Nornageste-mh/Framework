# -*- coding: utf-8 -*-
r"""从 A11yFramework 生成一个新作的骨架。

把「复制—改名—局部改写」这件事变成一条命令，并且保证：
  · 平台层整份拷贝、只换 namespace（不再手工改名）
  · 逐作文件从模板生成，占位符一次替换完
  · .ps1 保持 UTF-8 **带 BOM**（否则 PowerShell 5.1 按 GBK 解码 → 语法错误）
  · .cs 保持无 BOM 的 UTF-8

★ 本生成器**只生成 Unity（BepInEx）骨架**。KiriKiri Z（流水线 §3.3）与 Ren'Py（§3.4）
  没有可加载 .NET 插件的宿主，走 --route mono/il2cpp 会生成「看起来完整、实际装不进游戏」
  的半成品。所以这两条路线（以及 --gamedir 探测到的非 Unity 游戏）一律 **exit 2**，
  打印对应手册章节与手工最小文件清单；不会写任何文件。确认探测误判时用 --force-route。

用法：
    python tools/new_game.py --ns MyGameA11y --game MyGame --exe MyGame.exe ^
        --guid mygame.a11y.reader --title 《我的游戏》 --route mono --out .\MyGameA11y

    # 非 Unity 路线：显式声明后会被拒绝，并打印 §3.3 / §3.4 的手工清单
    python tools/new_game.py ... --route krkrz
    python tools/new_game.py ... --route renpy
"""
import argparse
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # A11yFramework 仓库根

PLACEHOLDER_FILES = [
    ("templates/game/Plugin.cs.template",        "mod/src/{ns}/Plugin.cs",            True),
    ("templates/game/TextProc.cs.template",      "mod/src/{ns}/TextProc.cs",          True),
    # 选项播报/数字键选择的逐作实现。平台层不认识任何游戏的选项结构
    # （否则就不再是「无游戏类型依赖」的冻结层），所以这个文件必须生成。
    # 早期版本漏了它，Plugin 却已经调 Choices.Update() → 新骨架 CS0103。
    ("templates/game/Choices.cs.template",       "mod/src/{ns}/Choices.cs",           True),
    ("templates/game/UiNav.Game.cs.template",    "mod/src/{ns}/UiNav.Game.cs",        True),
    ("templates/game/GameA11y.csproj.template",  "mod/src/{ns}/{ns}.csproj",          True),
    ("build/build.ps1.template",                 "mod/build.ps1",                     False),
    ("build/release.ps1.template",               "mod/release.ps1",                   False),
    ("build/makezip.ps1.template",               "mod/tools/makezip.ps1",             False),
    ("build/check-staged.ps1.template",          "tools/check-staged.ps1",            False),
    ("probe/run_probe.ps1.template",             "probe/run_probe.ps1",               False),
    ("probe/screenshot.ps1.template",            "probe/screenshot.ps1",              False),
    ("tools/lint_repeat.ps1",                    "tools/lint_repeat.ps1",             False),
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


def smoke_check(out, ns, route):
    """生成后的冒烟检查：**不只用 grep 占位符**。

    以前只检查「还有没有 {{NS}}」，于是下面这些问题都能一路生成成功、到第一次
    dotnet build 或第一次进游戏才炸：
      · csproj 被 @@ROUTE 裁成非法 XML（MSB4025）
      · UiNav.Game.cs 的 NameAlias 有大小写重复键（导航静默死亡）
      · Choices.cs / GlobalKeys.cs / l1-files.txt 根本没生成
    这里逐项机械核对，任何一项不过就非零退出 —— 骨架生成器不该产出「看起来完整」
    但第一次编译就失败的东西。
    """
    problems = []
    must = [
        "LICENSE", "NOTICE.md", "CHANGELOG.md", "README.md",
        "tools/l1-files.txt", "tools/compile_check.ps1",
        "mod/build.ps1", "mod/release.ps1",
        "mod/src/%s/Plugin.cs" % ns,
        "mod/src/%s/UiNav.Game.cs" % ns,
        "mod/src/%s/Choices.cs" % ns,
        "mod/src/%s/GlobalKeys.cs" % ns,
        "mod/src/%s/%s.csproj" % (ns, ns),
    ]
    for rel in must:
        if not os.path.isfile(os.path.join(out, rel.replace("/", os.sep))):
            problems.append("缺少文件：" + rel)

    # 1) csproj 必须能当 XML 解析
    csproj = os.path.join(out, "mod", "src", ns, ns + ".csproj")
    if os.path.isfile(csproj):
        try:
            ET.parse(csproj)
        except ET.ParseError as e:
            problems.append("csproj 不是合法 XML（MSB4025？）：%s" % e)

    # 2) 真实 UiNav.Game.cs 的 NameAlias 按 OrdinalIgnoreCase 查重
    ui = os.path.join(out, "mod", "src", ns, "UiNav.Game.cs")
    if os.path.isfile(ui):
        text, _ = read(ui)
        m = re.search(r"NameAlias\s*=", text)
        if not m:
            problems.append("UiNav.Game.cs 里找不到 NameAlias")
        elif "StringComparer.OrdinalIgnoreCase" not in text[m.start():m.start() + 400]:
            problems.append("UiNav.Game.cs 的 NameAlias 不是 OrdinalIgnoreCase 字典")
        else:
            tail = text[m.start():]
            keys = [k for k in re.findall(r'\{\s*"((?:[^"\\]|\\.)*)"\s*,', tail)]
            seen = {}
            for k in keys:
                lk = k.casefold()
                if lk in seen:
                    problems.append("NameAlias 大小写重复键：%r / %r（编译期不报，"
                                    "静态构造抛 ArgumentException）" % (seen[lk], k))
                else:
                    seen[lk] = k
            if not keys:
                problems.append("NameAlias 一个键都没解析到")

    # 3) 占位符与 @@ROUTE 标记不能残留（标记行形如 // @@ROUTE:mono@@）
    text_ext = {".cs", ".ps1", ".csproj", ".md", ".txt", ".gitignore", ".gitattributes"}
    for dirpath, _, files in os.walk(out):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            base = fn.lower()
            if ext not in text_ext and base not in (".gitignore", ".gitattributes"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                t = open(p, encoding="utf-8", errors="strict").read()
            except (UnicodeDecodeError, OSError):
                continue
            rel = os.path.relpath(p, out)
            if re.search(r"\{\{[A-Z]+\}\}", t):
                problems.append("残留占位符：%s" % rel)
            if re.search(r"(?m)^\s*(?://|#)?\s*@@(ROUTE|ENDROUTE)", t):
                problems.append("残留 @@ROUTE 标记行：%s" % rel)

    if problems:
        sys.exit("生成后自检失败（%d 项）：\n  - %s" % (len(problems), "\n  - ".join(problems)))
    print("自检通过：csproj XML / NameAlias 查重 / 关键文件 / 无占位符与路线标记")


# ============================ 非 Unity 路线守卫 ============================
# 背景（流水线 0.2.6 §3.3–§3.5）：KiriKiri Z 是原生 C++（没有 BepInEx/plugins 宿主，
# 唯一执行点是改归档里的启动脚本槽位），Ren'Py 是脚本运行时（没有编译、只有 .rpy
# 叠加层）。本生成器只认 BepInEx + A11yHost 的 C# 骨架，对这两条路线只能识别 + 拒绝。
# 清单内容全部来自 docs/无障碍补丁流水线.md §3.3 / §3.4，不是凭记忆写的。

NON_UNITY_ROUTES = {
    "krkrz": {
        "name": "KiriKiri Z",
        "section": "§3.3",
        "files": [
            "src/a11y.cpp                 # 导出 V2Link / V2Unlink / GetModuleThreadModel；",
            "                             # 走 iTVPFunctionExporter 虚表[1] QueryFunctionsByNarrowString",
            "src/zdsr_api.h               # platform/Zdsr.cs 同一契约的 C++ 实现（后端链/F9 循环）",
            "build/build.cmd              # VCVARS32；断言 VSCMD_ARG_TGT_ARCH=x86、/MACHINE:X86",
            "tools/build_injector.ps1     # 注入器：条目集合与顺序逐项比对，不接受「能启动」",
            "tools/inject_boot.py / .cs   # 改归档注入器（产物不入库；内层索引逐字节照抄，G37）",
            "data/a11y_labels*.ini        # 逐作标签表（主/字幕/界面语言各一份）",
            "tools/make_release.ps1       # 发布包 = 插件 DLL + plugin\\ 文件 + 安装/还原说明",
        ],
        "note": ("纪律：PE32/x86（x64 构建会「成功」但游戏静默不加载）；引擎**不会**自动加载\n"
                 "plugin\\*.dll，必须改游戏归档的启动脚本槽位；改过归档只能从原始备份整包恢复。"),
    },
    "renpy": {
        "name": "Ren'Py",
        "section": "§3.4",
        "files": [
            "mod/game/a11y_platform/00_contract.rpy       init -200  契约（单一默认 store + 具名槽位）",
            "mod/game/a11y_platform/90_plugin.rpy         init -190  逐作入口：GameName/版本/全部开关",
            "mod/game/a11y_platform/05_repeat.rpy         init -103  重读缓冲区（唯一朗读出口）",
            "mod/game/a11y_platform/01_speech.rpy         init -100  后端链（Tolk→NVDA→争渡→SAPI 子进程）",
            "mod/game/a11y_game/20_textproc.rpy           init  -60  文本清洗",
            "mod/game/a11y_game/30_choice.rpy             init  -60  选项",
            "mod/game/a11y_game/22_uialt.rpy              init  -55  逐作文案表",
            "mod/game/a11y_platform/10_renpy_adapter.rpy  init  -50  L2.5 引擎适配（接管 config.tts_function）",
            "mod/game/a11y_game/08_uialt.rpy              init  -45  焦点表 / 导航（focus_list 拉模型）",
            "mod/game/a11y_platform/06_keymap.rpy         init 1200  键位（必须晚于引擎 00keymap 的 1100）",
            "mod/game/a11y_platform/90_plugin.rpy         init 1300  validate → 启动 → 安装键位",
            "tools/rpa.py / check_boot.py / lint_patch.py / install.ps1 / make_release.ps1",
        ],
        "note": ("纪律：只有 init 顺序正确才生效（错一拍 = 静默失效，引擎 lint 仍 exit 0）；\n"
                 "部署走松散 .rpy 叠加层、**不碰 .rpa**；验收 = lint_patch.py 12 条静态断言 +\n"
                 "check_boot.py 八条启动正向证据（「没报错」≠「跑起来了」）。"),
    },
}

_KRK_PRODUCT_UTF16 = "TVP(KIRIKIRI)".encode("utf-16-le")
_KRK_PRODUCT_ASCII = b"TVP(KIRIKIRI)"


def _pe_machine(path):
    """返回 PE 的 Machine 值（0x014C=x86/PE32，0x8664=x64）；非 PE 返回 None。"""
    try:
        with open(path, "rb") as f:
            if f.read(2) != b"MZ":
                return None
            f.seek(0x3C)
            off = int.from_bytes(f.read(4), "little")
            if off <= 0 or off > 1024 * 1024:
                return None
            f.seek(off)
            if f.read(4) != b"PE\0\0":
                return None
            return int.from_bytes(f.read(2), "little")
    except OSError:
        return None


def _exe_has_tvp_product(path):
    """exe 的版本资源里是否出现 ProductName=TVP(KIRIKIRI)。

    没有 win32 资源解析依赖（那会让脚本只能在 Windows 跑），直接按字节找
    UTF-16LE / ASCII 的 "TVP(KIRIKIRI)" —— 是启发式，但足以区分 KiriKiri Z 与原版 TVP。
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return False
    return _KRK_PRODUCT_UTF16 in data or _KRK_PRODUCT_ASCII in data


def _looks_like_unity(gamedir):
    """目录里出现 <X>_Data\\Managed 或 il2cpp_data ⇒ 优先当 Unity，避免 data.xp3 之类误判。"""
    try:
        entries = os.listdir(gamedir)
    except OSError:
        return False
    for name in entries:
        p = os.path.join(gamedir, name)
        if not os.path.isdir(p):
            continue
        if os.path.isdir(os.path.join(p, "Managed")) or os.path.isdir(os.path.join(p, "il2cpp_data")):
            return True
    return False


def _renpy_layout(gamedir):
    """renpy/ 目录 + game/ 下至少一个 .rpa/.rpy/.rpyc ⇒ (renpy_dir, 例证列表)。"""
    renpy_dir = os.path.join(gamedir, "renpy")
    if not os.path.isdir(renpy_dir):
        return None
    game_dir = os.path.join(gamedir, "game")
    hits = []
    if os.path.isdir(game_dir):
        for root, _dirs, files in os.walk(game_dir):
            for fn in files:
                if fn.lower().endswith((".rpa", ".rpy", ".rpyc")):
                    hits.append(os.path.join(root, fn))
                    if len(hits) >= 8:
                        break
            if len(hits) >= 8:
                break
    return (renpy_dir, hits) if hits else None


def probe_non_unity(gamedir, exe):
    """探测 --gamedir 是否是非 Unity 路线。命中返回 (route, 证据列表)，否则 None。

    判定顺序：Unity 标志优先（防误判）→ KiriKiri Z → Ren'Py。
    KiriKiri Z 按流水线 P0 的特征：ProductName=TVP(KIRIKIRI) Z core，**或** data.xp3 + PE32。
    """
    if not gamedir or not os.path.isdir(gamedir):
        return None
    if _looks_like_unity(gamedir):
        return None

    exe_path = os.path.join(gamedir, os.path.basename(exe)) if exe else ""
    pe = _pe_machine(exe_path) if os.path.isfile(exe_path) else None
    has_xp3 = os.path.isfile(os.path.join(gamedir, "data.xp3"))
    evidence = []
    product = False
    if pe == 0x014C:
        evidence.append("exe 是 PE32（Machine=0x014C，32 位/x86）")
    if os.path.isfile(exe_path) and _exe_has_tvp_product(exe_path):
        product = True
        evidence.append("exe 字节里含 ProductName=TVP(KIRIKIRI)")
    if has_xp3:
        evidence.append("存在 data.xp3（KiriKiri 归档）")
    if product or (has_xp3 and pe == 0x014C):
        return ("krkrz", evidence)

    ren = _renpy_layout(gamedir)
    if ren:
        _rd, hits = ren
        rel = [os.path.relpath(h, gamedir) for h in hits]
        evidence = ["存在 renpy/ 目录",
                    "game/ 下有 %d 个 .rpa/.rpy/.rpyc（如 %s）" % (len(hits), "、".join(rel[:3]))]
        return ("renpy", evidence)
    return None


def reject_non_unity(route, evidence, requested_route):
    """打印手册章节 + 手工最小文件清单后 exit 2。绝不写文件。"""
    meta = NON_UNITY_ROUTES[route]
    print("")
    print("=" * 72)
    print("拒绝生成：非 Unity 路线（%s）不支持自动生成 Unity/BepInEx 骨架" % meta["name"])
    print("=" * 72)
    print("触发依据（%s）：" % ("显式 --route" if requested_route == route else "启发式探测"))
    for e in evidence:
        print("  - " + e)
    print("")
    print("为什么拒绝：本生成器只会产出 BepInEx + A11yHost 的 C# 骨架；%s" % meta["name"])
    print("没有可加载 .NET 插件的宿主（也没有 platform/ L1），生成出来只会是误导性半成品。")
    print("")
    print("请按《无障碍补丁流水线》%s（docs/无障碍补丁流水线.md）手工搭：" % meta["section"])
    for line in meta["files"]:
        print("  " + line)
    print("")
    print(meta["note"])
    print("")
    print("（若确认启发式探测误判，加 --force-route 跳过探测、按 --route 生成；本脚本不会删除文件。）")
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", required=True, help="C# namespace / 程序集名，例如 BelfryA11y")
    ap.add_argument("--game", required=True, help="MSBuild 属性前缀，例如 Belfry（-> BelfryGameDir）")
    ap.add_argument("--exe", required=True, help="游戏可执行文件名，例如 The Belfry.exe")
    ap.add_argument("--guid", required=True, help="BepInEx 插件 GUID")
    ap.add_argument("--title", required=True, help="游戏中文名，例如 《钟塔》")
    ap.add_argument("--route", required=True, choices=["mono", "il2cpp", "krkrz", "renpy"],
                    help="mono/il2cpp = 生成 Unity 骨架；krkrz = KiriKiri Z、renpy = Ren'Py，"
                         "这两条非 Unity 路线只做识别并拒绝（exit 2，打印流水线 §3.3/§3.4 的"
                         "手工最小文件清单），不生成半成品")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--version", default="0.1.0.0", help="纯数字四段版本号")
    ap.add_argument("--display", default=None, help="BepInEx 显示名，默认由 --title 推")
    ap.add_argument("--datadir", default=None, help="<Game>_Data 目录名，默认按 --exe 推")
    ap.add_argument("--gamedir", default="",
                    help="游戏安装目录；不给则生成的 csproj 与脚本保留 <游戏目录> 占位，需自行填")
    ap.add_argument("--merge", action="store_true",
                    help="输出目录非空时只补缺失文件：已存在的文件**跳过并打印**，不覆盖。"
                         "不加此开关时非空目录一律拒绝（防止误踩掉已填好的逐作代码）")
    ap.add_argument("--force-route", action="store_true",
                    help="跳过非 Unity 路线启发式探测，强制按 --route 生成。"
                         "只在确认探测误判（例如自制发行版改了目录结构）时使用")
    a = ap.parse_args()

    # ---- 路线守卫：非 Unity 游戏绝不能落进 Unity 骨架分支 ----
    # 先看显式声明（--route krkrz|renpy 不再被 argparse 当未知选项），
    # 再看 --gamedir 的启发式探测（防止用户「以为是 Unity」直接跑默认分支）。
    if a.route in NON_UNITY_ROUTES:
        reject_non_unity(a.route, ["显式指定 --route %s" % a.route], a.route)
    if a.gamedir and not a.force_route:
        probed = probe_non_unity(a.gamedir, a.exe)
        if probed:
            reject_non_unity(probed[0], probed[1], a.route)
    elif a.gamedir and a.force_route:
        print("警告：--force-route 已跳过非 Unity 路线探测，按 --route %s 生成 Unity 骨架。" % a.route)

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
    if os.path.isdir(out) and os.listdir(out) and not a.merge:
        sys.exit("输出目录非空，拒绝覆盖: " + out +
                 "（要往已有骨架里补文件，加 --merge：已存在的文件会跳过并打印）")

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
        "{{GAMEDIR}}": a.gamedir or r"<游戏目录>",
    }

    made = []
    skipped = []

    def emit(p, text, bom):
        """写一个生成文件。--merge 下已存在的文件**跳过并记录**，绝不静默覆盖。"""
        if a.merge and os.path.exists(p):
            skipped.append(p)
            return False
        write(p, text, bom)
        made.append(p)
        return True

    # ---- L1 平台层：整份拷贝，只换 namespace ----
    # ★ **唯一真源 = Framework 根 tools/l1-files.txt**（不是本文件里的常量，也不是
    #   platform/ 的目录顺序）。手写清单踩过两次同款事故：
    #     · 0.1.0.0 漏了 KeyEdge.cs → CS0103（UiNav 的按键边沿检测引用它）
    #     · 0.2.0.0 漏了 GlobalKeys.cs → CS0103（KeyEdge.cs 调 GlobalKeys.Reading /
    #       Held / SnapshotWords / FillOtherKeySnapshot / AnyNewOtherKeyHeld /
    #       ResetPressed），新作骨架**第一次编译就失败**
    #   所以这里不枚举、不猜顺序：逐行读清单拷贝，并**双向比对** platform/*.cs ——
    #   目录里多一个（清单没写）或少一个（清单写了但文件没了）都直接拒绝生成，
    #   免得「目录更新了、清单没改」漂移出第三种清单。
    #   逐作仓的 tools/l1-files.txt 是本清单的**原样副本**，compile_check.ps1 读它。
    platform_dir = os.path.join(ROOT, "platform")
    manifest_path = os.path.join(ROOT, "tools", "l1-files.txt")
    if not os.path.isfile(manifest_path):
        sys.exit("缺 tools/l1-files.txt —— 它是 L1 清单的唯一真源，不能靠脚本猜")
    manifest_text, _ = read(manifest_path)
    l1 = [ln.strip() for ln in manifest_text.splitlines()
          if ln.strip() and not ln.strip().startswith("#")]
    if not l1:
        sys.exit("tools/l1-files.txt 里一个文件名都没有")
    if len(set(l1)) != len(l1):
        sys.exit("tools/l1-files.txt 有重复文件名")
    actual = sorted(fn for fn in os.listdir(platform_dir)
                    if fn.endswith(".cs") and os.path.isfile(os.path.join(platform_dir, fn)))
    if sorted(l1) != actual:
        missed = sorted(set(actual) - set(l1))
        gone = sorted(set(l1) - set(actual))
        sys.exit("platform/*.cs 与 tools/l1-files.txt 不一致：\n"
                 "  · platform 有、清单没写：%s\n"
                 "  · 清单写了、platform 里没有：%s\n"
                 "平台层增删文件后必须同步改清单（它是唯一真源）。"
                 % (missed or "无", gone or "无"))
    if "GlobalKeys.cs" not in l1:
        sys.exit("tools/l1-files.txt 里没有 GlobalKeys.cs —— KeyEdge.cs 会引用 "
                 "GlobalKeys.*，少它必然 CS0103")
    for fn in l1:
        text, _ = read(os.path.join(platform_dir, fn))
        text = text.replace("namespace A11yFramework", "namespace " + a.ns)
        if "namespace " + a.ns not in text:
            sys.exit("%s 里没有找到 namespace A11yFramework，平台层可能被改过" % fn)
        emit(os.path.join(out, "mod", "src", a.ns, fn), text, False)

    # 逐作仓的 L1 清单：唯一真源的原样副本，供 compile_check.ps1 对账。
    emit(os.path.join(out, "tools", "l1-files.txt"), manifest_text, False)

    # ---- L2 契约层 ----
    text, _ = read(os.path.join(ROOT, "contract", "A11yHost.cs"))
    emit(os.path.join(out, "mod", "src", a.ns, "A11yHost.cs"),
         text.replace("namespace A11yFramework", "namespace " + a.ns), False)

    # ---- 模板文件 ----
    for src_rel, dst_rel, is_cs in PLACEHOLDER_FILES:
        src = os.path.join(ROOT, src_rel.replace("/", os.sep))
        text, bom = read(src)
        text = apply_route(text, a.route)
        text = substitute(text, subs)
        dst = os.path.join(out, dst_rel.format(ns=a.ns).replace("/", os.sep))
        # csproj 必须能当 XML 解析。删 @@ROUTE 段时最容易拼出「XML 注释里连续
        # 两个减号」之类的错误，MSB4025 会在第一次 dotnet build 才炸；这里先拦。
        if dst.endswith(".csproj"):
            # 探针 csproj 的 HintPath 里保留 <游戏目录> 占位（尖括号本身不是合法
            # XML 文本），校验时临时转义，只看标签结构是否正确 —— 真正要防的是
            # @@ROUTE 裁剪后标签/注释错配（MSB4025）。
            probe = text.replace("<游戏目录>", "&lt;游戏目录&gt;")
            try:
                ET.fromstring(probe)
            except ET.ParseError as e:
                sys.exit("生成的 csproj 不是合法 XML（%s）：%s\n  多半是 @@ROUTE 裁剪"
                         "后 XML 注释里出现了连续两个减号（MSB4025）" % (e, dst))
        # .cs 一律无 BOM；.ps1 保持原样（带 BOM）
        emit(dst, text, False if is_cs else bom)

    # ---- 文档骨架 ----
    for src_rel, dst_rel in DOC_FILES:
        src = os.path.join(ROOT, src_rel.replace("/", os.sep))
        text, bom = read(src)
        emit(os.path.join(out, dst_rel.replace("/", os.sep)),
             substitute(text, subs), bom)

    # ---- 许可证 ----
    # 取舍（见 _a11y-framework-sync/report-tools.md）：
    #   · 根 LICENSE 只放 Framework 的 MIT 原文，覆盖**本作自己的代码**；
    #   · BepInEx 6（LGPL-2.1）、Il2CppInterop（LGPL-3.0）、UnityDoorstop、
    #     NVDA Controller Client 等第三方文本放 licenses/，并在 NOTICE.md 里逐项指路；
    #     不把 LGPL 条款混写进根 LICENSE（那会让 MIT 授权范围变得含糊）。
    lic_text, _ = read(os.path.join(ROOT, "LICENSE"))
    emit(os.path.join(out, "LICENSE"), lic_text, False)

    # 只拷**本路线实际随包组件**的许可证原文。Framework 的 licenses/ 是一张
    # 全量清单（还带三份姊妹作的真实 THIRD-PARTY-NOTICES 范例），整目录拷进
    # 逐作仓会让发布包里混入别作的通告与根本不随包的组件 —— 已有作品实测踩过。
    lic_src = os.path.join(ROOT, "licenses")
    lic_dst = os.path.join(out, "mod", "licenses")
    os.makedirs(lic_dst, exist_ok=True)
    lic_wanted = ROUTE_LICENSE_FILES[a.route]
    lic_copied = 0
    for fn in sorted(os.listdir(lic_src)):
        sp = os.path.join(lic_src, fn)
        if not os.path.isfile(sp):
            continue
        # example-* 是姊妹作发布包里的真实范例（含别的作品名称与 AppID）；
        # *.patch 是上游补丁片段。两者只在 Framework 里留档，不进逐作仓。
        if fn.startswith("THIRD-PARTY-NOTICES.example-") or fn.endswith(".patch"):
            continue
        if fn not in lic_wanted:
            continue
        dp = os.path.join(lic_dst, fn)
        if a.merge and os.path.exists(dp):
            skipped.append(dp)
            lic_copied += 1
            continue
        shutil.copy2(sp, dp)
        lic_copied += 1
    if lic_copied != len(lic_wanted):
        sys.exit("licenses/ 里缺本路线需要的许可证：期望 %s，实际只拷到 %d 个"
                 % (sorted(lic_wanted), lic_copied))

    # ---- 根文件 ----
    for fn in (".gitignore", ".gitattributes"):
        sp = os.path.join(ROOT, fn)
        dp = os.path.join(out, fn)
        if not os.path.isfile(sp):
            continue
        if a.merge and os.path.exists(dp):
            skipped.append(dp)
            continue
        shutil.copy2(sp, dp)

    # ---- 合规三件套骨架（LICENSE 上面已拷；这里生成 NOTICE / CHANGELOG）----
    emit(os.path.join(out, "NOTICE.md"), NOTICE_SKELETON.format(
        ns=a.ns, title=a.title.strip("《》"), route=a.route,
        route_rows=ROUTE_NOTICE_ROWS[a.route]), False)
    emit(os.path.join(out, "CHANGELOG.md"), CHANGELOG_SKELETON.format(
        ns=a.ns, version=a.version), False)

    # compile_check.ps1 有两种模式（脚本里自动判断）：
    #   · Framework 仓根（有 platform/）→ 老行为：临时工程编译，证明 L1 无游戏类型依赖
    #   · 逐作仓根（有 mod/src/）→ 静态守卫：L1 清单齐全 / NameAlias 大小写重复 /
    #     lint_repeat；不依赖游戏目录
    # ★ 不把 --gamedir 硬编码进 compile_check.ps1：那会让每个生成出来的脚本
    #   都带着作者本机的绝对路径，换机器就错，而且会随仓库提交泄漏路径。
    #   compile_check 的默认值本来就读环境变量 A11Y_GAMEDIR；这里改为生成一个
    #   可选的小助手 tools\set-gamedir.ps1，由使用者自己 dot-source 或复制。
    # 注意保留 BOM —— 它是 .ps1，PS 5.1 读无 BOM 的中文脚本会直接语法错误。
    cc_text, cc_bom = read(os.path.join(ROOT, "tools", "compile_check.ps1"))
    emit(os.path.join(out, "tools", "compile_check.ps1"), cc_text, True)
    if a.gamedir:
        emit(os.path.join(out, "tools", "set-gamedir.ps1"),
             "# 在**当前** PowerShell 会话里设置 A11Y_GAMEDIR，供 tools\\compile_check.ps1\n"
             "# 的默认 -GameDir 读取。换机器/换会话时改这里的值，或直接跑\n"
             "#   powershell -File tools\\compile_check.ps1 -GameDir \"<游戏目录>\"\n"
             "# 本文件是 --gamedir 生成的一次性助手，不要提交真实的个人路径。\n"
             '$env:A11Y_GAMEDIR = "%s"\n'
             'Write-Host "A11Y_GAMEDIR = $env:A11Y_GAMEDIR"\n' % a.gamedir, True)

    # README 骨架（流水线 §6 P7 的节名，逐作填内容）
    readme = os.path.join(out, "README.md")
    if not os.path.exists(readme):
        emit(readme, README_SKELETON.format(
            ns=a.ns, title=a.title.strip("《》"), guid=a.guid, route=a.route), False)
    else:
        # README 永远不覆盖（逐作自述是人的劳动成果）；--merge 时也要记进跳过列表，
        # 否则摘要里的「跳过 N 个」会和实际文件数对不上。
        skipped.append(readme)

    smoke_check(out, a.ns, a.route)

    total = sum(len(fs) for _, _, fs in os.walk(out))
    print("已渲染 %d 个文件，本作骨架共 %d 个文件 -> %s" % (len(made), total, out))
    if skipped:
        print("跳过 %d 个已存在的文件（--merge 不覆盖）：" % len(skipped))
        for p in skipped[:40]:
            print("  - %s" % os.path.relpath(p, out))
        if len(skipped) > 40:
            print("  ... 其余 %d 个" % (len(skipped) - 40))
    print()
    print("下一步（按这个顺序）：")
    print("  1. 填 mod/src/%s/UiNav.Game.cs  —— 别名表与姓名框探测，**每一条都要有依据**" % a.ns)
    print("  2. 填 mod/src/%s/TextProc.cs    —— 先用 P0 导出的剧本表离线跑规则" % a.ns)
    print("  3. 填 mod/src/%s/Plugin.cs      —— 配置项里的实测数字与补丁点（反编译实查）" % a.ns)
    print("  4. 填 mod/src/%s/Choices.cs   —— 选项读取/数字键，骨架只留了空 Update" % a.ns)
    print("  5. 填 probe/、README.md、NOTICE.md、CHANGELOG.md；然后 cd mod; .\\build.ps1")
    print()
    print("平台层（platform/ 下全部 %d 个 .cs，含 GlobalKeys/Hotkey/Zdsr）**不要再改** ——"
          % len(l1))
    print("改了就不再是冻结层；逐作仓的 tools/l1-files.txt 是它的清单。")


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

## 自检（不需要游戏目录）

@@F@@powershell
# 逐作仓静态守卫：L1 清单 / NameAlias 大小写重复 / 重读缓冲区出口
powershell -File tools\\compile_check.ps1

# 显式指定要检查的别名表（默认是 mod\\src\\{ns}\\UiNav.Game.cs）
powershell -File tools\\compile_check.ps1 -GameSrc mod\\src\\{ns}\\UiNav.Game.cs
@@F@@

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


ROUTE_NOTICE_ROWS = {
    "mono": """| BepInEx | 5.4.23.5（TODO 按实际包核对） | MIT | licenses/MIT-BepInEx.txt |
| HarmonyX | 随 BepInEx 5 | MIT | licenses/MIT-HarmonyX.txt |
| UnityDoorstop | 随 BepInEx 5（winhttp.dll） | LGPL-2.1 | licenses/LGPL-2.1-UnityDoorstop.txt |
| NVDA Controller Client | nvda_2026.2（TODO 核对） | LGPL-2.1 | licenses/LGPL-2.1-NVDA-ControllerClient.txt |""",
    "il2cpp": """| BepInEx | 6.0.0-be.788（TODO 按实际包核对） | LGPL-2.1 | licenses/LGPL-2.1-BepInEx.txt |
| HarmonyX | 随 BepInEx 6 | MIT | licenses/MIT-HarmonyX.txt |
| UnityDoorstop | 随 BepInEx 6（winhttp.dll） | LGPL-2.1 | licenses/LGPL-2.1-UnityDoorstop.txt |
| Il2CppInterop | 随 BepInEx 6 | LGPL-3.0 | licenses/LGPL-3.0-Il2CppInterop.txt |
| NVDA Controller Client | nvda_2026.2（TODO 核对） | LGPL-2.1 | licenses/LGPL-2.1-NVDA-ControllerClient.txt |""",
}

# 逐作仓 mod\licenses\ 里只保留**本路线实际随包组件**的许可原文。
# 判定依据是发布包里真实出现的二进制：
#   Mono：BepInEx 5（BepInEx.dll / 0Harmony.dll）、UnityDoorstop（winhttp.dll）、
#         NVDA Controller Client（两个 nvdaControllerClient.dll）
#   IL2CPP：BepInEx 6（Core / Unity.IL2CPP / Unity.Common）、HarmonyX（0Harmony.dll）、
#           UnityDoorstop（winhttp.dll）、Il2CppInterop（Il2CppInterop.Runtime.dll）、
#           NVDA Controller Client
# BepInEx 5 自带的 Harmony 是 HarmonyX 分支，所以用 MIT-HarmonyX.txt 覆盖；
# 不要整目录拷 licenses/ —— 那会把别作的 THIRD-PARTY-NOTICES 与不随包的
# 组件（Il2CppInterop、AssetRipper、Cpp2IL 等）一起塞进发布包。
ROUTE_LICENSE_FILES = {
    "mono": {
        "MIT-BepInEx.txt",
        "MIT-HarmonyX.txt",
        "LGPL-2.1-UnityDoorstop.txt",
        "LGPL-2.1-NVDA-ControllerClient.txt",
    },
    "il2cpp": {
        "LGPL-2.1-BepInEx.txt",
        "MIT-HarmonyX.txt",
        "LGPL-2.1-UnityDoorstop.txt",
        "LGPL-3.0-Il2CppInterop.txt",
        "LGPL-2.1-NVDA-ControllerClient.txt",
    },
}

NOTICE_SKELETON = """# 第三方组件与免责声明 / Third-Party Notices

> 本文件是 [A11yFramework](https://github.com/Nornageste-mh/Framework.git) 生成的骨架，
> **发布前必须按实际打进发布包的二进制逐项核对**，把 TODO 全部改掉。
> 根目录 [`LICENSE`](LICENSE)（MIT）**只覆盖本作自己的代码**；下表第三方组件不受它授权，
> 适用各自的许可条款，原文在 `mod/licenses/`（发布包里是 `licenses/`），必须随二进制分发。

## 1. 本作

- 名称：{title} 无障碍补丁（程序集 `{ns}`）
- 引擎路线：{route}
- 本作代码许可：MIT，见根目录 [`LICENSE`](LICENSE)
- 本项目是**非官方**第三方无障碍补丁

## 2. 随包分发的第三方二进制

| 组件 | 版本 | 许可 | 许可证文本 |
|---|---|---|---|
{route_rows}

> TODO 发布前按 `package\\` 里实际存在的文件重列：版本号从下载的 zip 名 / 程序集
> FileVersion 抄，不要沿用本骨架的示例值；新增或移除组件都要同步这张表。
> 若使用 `licenses/il2cppinterop-pr277.patch` 对应的修复版 Il2CppInterop.Runtime.dll，
> 还要在发布说明里写明来源（BepInEx 上游 PR #277）与修改内容。

## 3. 非官方声明

本软件是非官方的第三方无障碍辅助项目，与《{title}》的开发商、发行商、平台
及任何相关权利方**不存在**隶属、合作、赞助、授权或背书关系。相关商标、作品名称
与内容的全部权利归各自权利人所有。

## 4. 免责

本软件按「现状」提供，不附带任何明示或默示担保。在适用法律允许的最大范围内，
作者与贡献者对因使用或无法使用本软件产生的任何直接、间接、附带、特殊或后果性
损害不承担责任，包括但不限于存档损坏/丢失、游戏无法启动或崩溃、账号被限制、
与服务条款或 EULA 相关的争议。是否使用由你自行决定并承担全部风险。

## 5. 禁止随包的内容

发布包**不得**包含：`BepInEx\\interop\\`、`BepInEx\\unity-libs\\`、反编译/解包产物、
游戏原始资源与剧本、开发机配置（`BepInEx\\config\\{ns}.cfg` 等）。这是 IP 与合规红线，
`mod\\build.ps1` 与 `mod\\release.ps1` 会机械拦截。
"""

CHANGELOG_SKELETON = """# 更新日志

> 版本号规则：**纯数字分段（例如 0.1.0.1），2~4 段**，必须与 `Plugin.cs` 的
> `const string Version` 和 csproj 的 `<Version>` **完全一致**。
> 含字母的写法（0.1.0a）会让 BepInEx 判定 `version is invalid` 并**静默跳过整个插件**
> —— 日志里只有一行 Warning，表现是模组完全没加载。想表达「第三版修订」用第四位：0.1.0.3。

## 0.0.0.1（骨架生成）

> 这是骨架自带的**示例条目**。第一次真正发版时，把它改成上面规则允许的版本号
> （与插件版本一致），并重写下面每一条；不要保留「TODO」字样发出去。

- 由 A11yFramework 生成 `{ns}` 骨架（当前插件版本占位 `{version}`）。
- 未复测声明：TODO 本版本尚未在实机上按 `docs/templates/测试问卷.md` 复测
  （或：已复测，环境/结论写在这里）。
- 平台层从 Framework 整份拷贝、未修改；L1 文件清单见 `tools/l1-files.txt`。
- 已知问题：TODO 与 README 的「已知问题」保持一致。
"""


if __name__ == "__main__":
    main()
