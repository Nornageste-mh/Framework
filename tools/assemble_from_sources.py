# -*- coding: utf-8 -*-
r"""从三个已发布仓库**重新组装** A11yFramework 的 L1 平台层与 licenses\。

    python tools/assemble_from_sources.py --study <三个仓库的克隆根目录>

注意：本脚本只重写 platform\ 与 licenses\，**不会碰手写的**
README / contract/A11yHost.cs / templates/game/*.template。

原始说明：从三个已发布仓库组装 A11yFramework（可复用的平台层 + 契约层）。

设计依据：docs/无障碍补丁流水线.md（§2 三层架构、附录 A 可复用文件清单）

编码纪律（流水线 §5.1 G4/G5）：
  · .cs / .py       无 BOM 的 UTF-8，按字节读写，只做定点替换，保留原换行符
  · .ps1            必须保持 UTF-8 **带 BOM**，否则 PowerShell 5.1 按 GBK 解码
  · 许可证 / 二进制  逐字节拷贝
"""
import os, re, shutil, hashlib

import argparse

_ap = argparse.ArgumentParser(
    description="从三个已发布仓库重新组装 L1 平台层与 licenses\\（会覆盖 platform\\ 与 licenses\\）")
_ap.add_argument("--study", default=r"D:\work\a11y-study",
                 help="三个仓库克隆的根目录，下面应有 belfry / noexistence / transparenther")
_ap.add_argument("--out", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 help="A11yFramework 仓库根目录，默认本脚本的上一级")
_ARGS = _ap.parse_args()

STUDY = _ARGS.study
BEL = os.path.join(STUDY, "belfry")
NOE = os.path.join(STUDY, "noexistence")
TRA = os.path.join(STUDY, "transparenther")
OUT = _ARGS.out
SRC_BEL = os.path.join(BEL, r"mod\src\BelfryA11y")

report = []


def rb(p):
    with open(p, "rb") as f:
        return f.read()


def wb(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def read_text(p):
    raw = rb(p)
    bom = raw.startswith(b"\xef\xbb\xbf")
    if bom:
        raw = raw[3:]
    return raw.decode("utf-8"), bom


def write_text(p, text, bom=False):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    wb(p, data)


def copy_bytes(src, dst):
    wb(dst, rb(src))
    report.append(("copy", os.path.relpath(dst, OUT), len(rb(src))))


def copy_text(src, dst, subs=()):
    text, bom_in = read_text(src)
    n = 0
    for a, b in subs:
        n += text.count(a)
        text = text.replace(a, b)
    write_text(dst, text, bom_in)
    report.append(("tmpl", os.path.relpath(dst, OUT), n))


BANNER = """    // ========================================================================
    // A11yFramework · L1 平台层（**冻结层**，逐作整份复用，不重写）
    //
    // 来源：三个已发布仓库里最完整的一份（《钟塔》BelfryForAccessibility），
    //       并已按《无障碍补丁流水线》§2.2 把对 Plugin.* 的引用改指 A11yHost.*。
    //
    // 逐作使用时**只允许改两处**：
    //   1) namespace —— 由 tools/new_game.py 自动替换，不要手改
    //   2) 本文件里所有 A11yHost.* 成员由契约层（contract/A11yHost.cs）提供，
    //      逐作不需要改这里的代码，只需要在 Plugin.Awake 里把值填进去
    //
    // 下文注释里出现的《钟塔》/《透明的她与真实的我》/《不/存在的你，和我》
    // 是**实测背景的记录**。保留原文是为了不丢掉「这条规则是被哪次事故逼出来的」
    // 这一证据（见流水线 §1.3、§5）。不要因为「看起来像别的项目」而删掉。
    //
    // 纪律：本层**绝不允许**引用任何游戏类型（Assembly-CSharp 里的任何东西）、
    //       任何逐作配置项、Il2CppInterop / Il2CppSystem。
    //       由 tools/compile_check.ps1 编译验证（不引用 Assembly-CSharp）。
    // ========================================================================
"""


def add_banner(text, ns_line="namespace A11yFramework"):
    m = re.search(r"^[ \t]*" + re.escape(ns_line) + r"[ \t]*\r?$", text, re.M)
    if not m:
        raise SystemExit("找不到 namespace 锚点: " + ns_line)
    nl = "\r\n" if "\r\n" in text else "\n"
    brace = text.index("{", m.end())
    at = text.index(nl, brace) + len(nl)
    return text[:at] + BANNER.replace("\n", nl) + text[at:]


def finish(text, name):
    """namespace 替换 + 断言无 Plugin. 残留 + 加冻结层横幅。"""
    text = text.replace("Plugin.", "A11yHost.")
    if "Plugin." in text:
        raise SystemExit("%s 还剩 Plugin. 引用" % name)
    text = text.replace("namespace BelfryA11y", "namespace A11yFramework")
    return add_banner(text)


def build_platform():
    # KeyEdge.cs 按流水线 §1.2 被归成「belfry 的按键边沿检测」，
    # 但平台层的 UiNav.cs 引用它 14 处 —— 它其实是 L1，本仓库把它提升为冻结层。
    #
    # Zdsr.cs（争渡读屏后端）与 Hotkey.cs（按键描述解析）是 0.2.0.0 新增的 L1 文件：
    # **必须列在这里**。main() 会先把 platform\ 整个删掉再按这张表重建 ——
    # 漏一个文件就等于把平台层的新能力删掉，而且 report 里只会少一行，不会报错。
    for name in ("Speech.cs", "Nvda.cs", "Sapi.cs", "Zdsr.cs", "Hotkey.cs", "KeyEdge.cs"):
        text, _ = read_text(os.path.join(SRC_BEL, name))
        n = text.count("Plugin.")
        write_text(os.path.join(OUT, "platform", name), finish(text, name), False)
        report.append(("L1", name, "Plugin.*->%d" % n))


def build_uinav_split():
    text, _ = read_text(os.path.join(SRC_BEL, "UiNav.cs"))
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)

    def find(pred, start=0, what=""):
        for i in range(start, len(lines)):
            if pred(lines[i]):
                return i
        raise SystemExit("找不到锚点: " + what)

    a_doc = find(lambda s: "设置面板里那些" in s, 0, "NameAlias 文档注释")
    a1 = a_doc
    while a1 > 0 and lines[a1 - 1].strip().startswith("///"):
        a1 -= 1
    if lines[a1].strip() != "/// <summary>" or lines[a_doc - 1].strip() != "/// <summary>":
        raise SystemExit("NameAlias 文档注释起始锚点对不上: " + repr(lines[a1]))
    a_open = find(lambda s: "NameAlias =" in s, a1, "NameAlias 声明")
    a_end = find(lambda s: s.strip() == "};", a_open, "NameAlias 结束")

    b1 = find(lambda s: s.strip().startswith("// ================= 姓名输入框"), 0, "姓名输入框区块")
    b_sig = find(lambda s: "InputFieldRoleName(TMP_InputField inf)" in s, b1, "InputFieldRoleName")
    depth, started, i = 0, False, b_sig
    while i < len(lines):
        depth += lines[i].count("{") - lines[i].count("}")
        if "{" in lines[i]:
            started = True
        if started and depth == 0:
            break
        i += 1
    b_end = i

    game = lines[a1:a_end + 1] + [""] + lines[b1:b_end + 1]
    engine = lines[:a1] + lines[a_end + 1:b1] + lines[b_end + 1:]

    # _inputRoles 的声明必须留在**引擎**侧：引擎的 Scan() 每次重扫都要 Clear() 它
    # （实例 ID 会在对象销毁后被复用），而逐作区的 InputFieldRoleName 只是读写它。
    # 放在逐作区会让引擎编不过 —— 这是 tools/compile_check.ps1 抓出来的（CS0103）。
    hit = [i for i, s in enumerate(game) if "_inputRoles = new Dictionary" in s]
    if len(hit) != 1:
        raise SystemExit("在逐作区里找不到唯一的 _inputRoles 声明")
    game.pop(hit[0])

    anchor = "        private const float SceneSettleSeconds = 1.5f;"
    if anchor not in nl.join(engine):
        raise SystemExit("找不到 SceneSettleSeconds 锚点")
    engine_decl = [
        "",
        "        // 输入框角色缓存（实例 ID -> 「姓氏」/「名字」/空串）。",
        "        // 声明留在引擎侧的理由：Scan() 每次重扫都要 Clear() 它（实例 ID 会在",
        "        // 对象销毁后被复用），而真正算出角色的是逐作区的 InputFieldRoleName",
        "        // —— 那边把游戏自己的类型名写死在反射里，所以那块属于逐作层。",
        "        private static readonly Dictionary<int, string> _inputRoles = new Dictionary<int, string>();",
    ]
    idx = [i for i, s in enumerate(engine) if s == anchor]
    if len(idx) != 1:
        raise SystemExit("SceneSettleSeconds 锚点不唯一")
    engine = engine[:idx[0] + 1] + engine_decl + engine[idx[0] + 1:]
    engine_text = nl.join(engine)
    if "internal static class UiNav" not in engine_text:
        raise SystemExit("UiNav 类声明锚点对不上")
    engine_text = engine_text.replace(
        "internal static class UiNav", "internal static partial class UiNav", 1)

    old_diag = ("        private static void Diag(string msg)" + nl +
                "        {" + nl +
                "            try" + nl +
                "            {" + nl +
                "                if (A11yHost.CfgDiagLog != null && A11yHost.CfgDiagLog.Value && A11yHost.Log != null)" + nl +
                "                    A11yHost.Log.LogInfo(\"[UiNav] \" + msg);" + nl +
                "            }" + nl +
                "            catch { }" + nl +
                "        }")
    new_diag = ("        private static void Diag(string msg)" + nl +
                "        {" + nl +
                "            A11yHost.Diag(\"[UiNav] \" + msg);" + nl +
                "        }")
    engine_text = finish(engine_text, "UiNav.cs")
    if old_diag not in engine_text:
        raise SystemExit("UiNav.Diag 原文对不上")
    engine_text = engine_text.replace(old_diag, new_diag, 1)

    write_text(os.path.join(OUT, "platform", "UiNav.cs"), engine_text, False)
    report.append(("L1 split", "UiNav.cs", "引擎 %d 行" % len(engine)))
    report.append(("L1 split", "UiNav.Game.cs", "逐作 %d 行" % len(game)))
    return nl.join(game), nl


def assert_sources_not_stale():
    r"""组装**之前**先确认源仓库不比本仓库旧。

    为什么要有这一道：本脚本会把 platform\ 删掉再重建，而它读的是三个补丁仓库的克隆。
    如果那份克隆落后于平台层（例如克隆还停在引入争渡后端之前），跑一遍就会把
    platform\Zdsr.cs、Hotkey.cs 与 Speech.cs 的 CycleAvailable **静默删掉** ——
    这正是流水线 §1.3 说的「平台层单向退化」，而且退化完 git status 看起来还挺干净。
    所以：宁可拒绝运行，也不许把新能力组装没。
    """
    need_files = ("Zdsr.cs", "Hotkey.cs")
    for fn in need_files:
        p = os.path.join(SRC_BEL, fn)
        if not os.path.isfile(p):
            raise SystemExit(
                "源仓库太旧：%s 里没有 %s。\n"
                "这会删掉平台层的新能力，已拒绝运行。\n"
                "请先把三个补丁仓库的克隆更新到含争渡后端的提交（或改 --study 指向它们）。"
                % (SRC_BEL, fn))

    speech = os.path.join(SRC_BEL, "Speech.cs")
    text, _ = read_text(speech)
    if "CycleAvailable" not in text:
        raise SystemExit(
            "源仓库太旧：%s 里的 Speech.cs 没有 CycleAvailable（切换语音后端）。\n"
            "跑下去会把平台层的这一能力删掉，已拒绝运行。\n" % speech)


def main():
    # 只清掉本脚本**自己生成**的目录。
    # 绝不 rmtree 整棵树 —— 仓库里还有手写的 README / A11yHost.cs / 文档模板，
    # 删掉它们等于把人工成果一起清空（第一次跑这个脚本时就踩到了）。
    assert_sources_not_stale()
    for sub in ("platform", "licenses"):
        d = os.path.join(OUT, sub)
        if os.path.isdir(d):
            shutil.rmtree(d)
    os.makedirs(OUT, exist_ok=True)

    game_block, nl = build_uinav_split()
    build_platform()
    write_text(os.path.join(OUT, "templates", "game", "UiNav.Game.cs.template"), game_block, False)

    seen = {}
    for tag, root in (("belfry", BEL), ("noexistence", NOE), ("transparenther", TRA)):
        d = os.path.join(root, r"mod\licenses")
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            sp = os.path.join(d, fn)
            if not os.path.isfile(sp):
                continue
            h = hashlib.sha256(rb(sp)).hexdigest()[:12]
            if fn in seen and seen[fn][0] == h:
                continue
            out_fn = fn
            if fn == "THIRD-PARTY-NOTICES.txt":
                route = "il2cpp" if tag == "noexistence" else "mono"
                out_fn = "THIRD-PARTY-NOTICES.example-%s-%s.txt" % (tag, route)
            seen.setdefault(out_fn, (h, sp))
            copy_bytes(sp, os.path.join(OUT, "licenses", out_fn))

    # 顺序有讲究：长串先替换，否则 "The Belfry" 会先把 "The Belfry_Data" 咬掉一半。
    SUBS = [
        ("D:\\Steam\\steamapps\\common\\钟塔 Belfry", "{{GAMEDIR}}"),
        ("BelfryA11y", "{{NS}}"),
        ("BelfryGameDir", "{{GAME}}GameDir"),
        ("The Belfry.exe", "{{EXE}}"),
        ("The Belfry_Data", "{{DATADIR}}"),
        ("The Belfry", "{{PROCNAME}}"),
        ("Belfry A11y Probe", "{{TITLE}} A11y Probe"),
        ("《钟塔》", "《{{TITLE}}》"),
    ]
    copy_text(os.path.join(BEL, r"mod\build.ps1"), os.path.join(OUT, "build", "build.ps1.template"), SUBS)
    copy_text(os.path.join(BEL, r"mod\release.ps1"), os.path.join(OUT, "build", "release.ps1.template"), SUBS)
    copy_text(os.path.join(BEL, r"mod\tools\makezip.ps1"), os.path.join(OUT, "build", "makezip.ps1.template"))
    copy_text(os.path.join(BEL, r"tools\check-staged.ps1"), os.path.join(OUT, "build", "check-staged.ps1.template"))
    for fn in ("run_probe.ps1", "screenshot.ps1"):
        sp = os.path.join(BEL, "probe", fn)
        if os.path.isfile(sp):
            copy_text(sp, os.path.join(OUT, "probe", fn + ".template"), SUBS)
    copy_text(os.path.join(BEL, r"probe\plugin\ProbePlugin.cs"),
              os.path.join(OUT, "templates", "probe", "ProbePlugin.cs.template"), SUBS)
    copy_text(os.path.join(BEL, r"probe\plugin\BelfryA11yProbe.csproj"),
              os.path.join(OUT, "templates", "probe", "Probe.csproj.template"), SUBS)
    copy_bytes(os.path.join(BEL, ".gitattributes"), os.path.join(OUT, ".gitattributes"))

    # 组装完再扫一遍：模板里不该残留上一作的名字。
    # 第一次组装就漏掉了进程名 'The Belfry'、'The Belfry_Data' 与探针里的
    # "Belfry A11y Probe" —— 靠人眼 diff 是看不出来的，所以做成机械断言。
    # 只扫**本脚本生成**的文件。手写的 README / Plugin.cs.template 里
    # 引用《钟塔》《透明的她》是**实测背景的记录**，是刻意保留的证据，不算残留。
    left = []
    # licenses\ 是三作的**原样拷贝**（第三方的许可证与声明范例），
    # 里面出现旧仓库名是应该的，不参与残留检查。
    generated = [os.path.join(OUT, p.replace("\\", os.sep)) for _, p, _ in report
                 if not p.startswith("licenses")]
    for fp in generated:
        if not os.path.isfile(fp):
            continue
        try:
            s = rb(fp).decode("utf-8")
        except Exception:
            continue
        for tok in ("BelfryA11y", "BelfryGameDir", "The Belfry", "钟塔 Belfry"):
            if tok in s:
                left.append((os.path.relpath(fp, OUT), tok))
    if left:
        print("!!! 模板里残留上一作的名字，请补进 SUBS：")
        for p, t in left:
            print("      %s  <- %s" % (p, t))
    else:
        print("残留检查：模板里没有上一作的名字。")

    print("=== 组装报告 ===")
    for kind, path, n in report:
        print("%-10s %-48s %s" % (kind, path, n))
    print("\n输出目录:", OUT)


if __name__ == "__main__":
    main()
