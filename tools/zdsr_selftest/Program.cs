// ============================================================================
// A11yFramework 平台层的机械自检（控制台，不依赖 Unity 运行时 / BepInEx）
//
// 覆盖两块**看不见的路径**：
//
//   A. platform/Zdsr.cs（争渡读屏后端）
//      争渡的授权位（GetSpeakState=2）在开发机上无法稳定复现，「跑一遍游戏听一下」
//      既不是机械验证、也覆盖不到失败路径。而这一级最容易错的地方恰恰全在暗处：
//        · 委托签名 / 字符集 / 调用约定错了 → 文本送过去是乱码或直接崩
//        · DLL 不在（大多数玩家的机器）→ 必须判不可用并让 Speech 往下走 SAPI
//        · 未授权时 Speak() 也返回 0 → 拿返回值当判据就会「日志一片绿、耳朵一片安静」
//        · 读屏中途被关掉 / 后打开 → 掉线要能恢复，且不能每句台词都刷一次握手
//      所以这里用一个桩 DLL（zdsr_stub.c）把上述状态全部造出来，再逐条断言。
//
//   B. platform/Hotkey.cs（"F9" / "Alt+Shift+F9" 这类按键描述）
//      解析层是纯逻辑，可以完全离线断言；Unity 的 Input 调用不在本自检范围内。
//
// 跑法：tools\zdsr_selftest\run.ps1
//   本程序直接编译 ../../platform/Zdsr.cs 与 ../../platform/Hotkey.cs（同一份源码，
//   不是副本）—— 这也是这两个文件不许引用 A11yHost / Plugin / BepInEx 的原因。
//   Hotkey.cs 需要 UnityEngine.KeyCode（枚举，编译期常量），由 run.ps1 从游戏目录取。
// ============================================================================

using System;
using System.IO;
using System.Text;
using System.Threading;

internal static class Program
{
    private static int _pass;
    private static int _fail;

    private static string _root;              // bin\
    private static string _stubDir;           // 带 Braille 的桩（对应 1.0.0.5）
    private static string _stubNoBrailleDir;  // 不带 Braille 的桩（对应 1.0.0.1）
    private static string _stubMismatchDir;   // InitTTS 固定返回 1（版本不匹配）
    private static string _emptyDir;          // 空目录（模拟「没装争渡」）
    private static string _logPath;           // 桩 DLL 的调用日志
    private static string _dllPath;           // 当前桩 DLL 的完整路径

    private static int Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;

        _root = args.Length > 0 ? args[0] : AppDomain.CurrentDomain.BaseDirectory;
        _stubDir = Path.Combine(_root, "stub");
        _stubNoBrailleDir = Path.Combine(_root, "stub_nobraille");
        _stubMismatchDir = Path.Combine(_root, "stub_mismatch");
        _emptyDir = Path.Combine(_root, "stub_empty");
        _logPath = Path.Combine(_root, "calls.log");

        Console.WriteLine("=== A11yFramework 平台层自检（Zdsr.cs / Hotkey.cs）===");
        Console.WriteLine("桩目录: " + _stubDir);

        // 桩 DLL 在进程内被 LoadLibrary 之后**文件会被锁住**，所以不同变体用不同目录，
        // 全程只摆放一次，中途不覆盖（覆盖会 IOException —— 这是踩过的坑）。
        try
        {
            Prepare(_stubDir, "zdsr_stub.dll");
            Prepare(_stubNoBrailleDir, "zdsr_stub_nobraille.dll");
            Prepare(_stubMismatchDir, "zdsr_stub_initmismatch.dll");
            Directory.CreateDirectory(_emptyDir);
        }
        catch (Exception e)
        {
            Console.WriteLine("准备桩 DLL 失败: " + e.Message);
            return 2;
        }
        Console.WriteLine();

        Console.WriteLine("### A. 争渡（ZDSR）后端");
        Case_MissingDll();
        Case_NotAuthorized();
        Case_Available_Idle();
        Case_Available_Speaking();
        Case_Speak_Parameters();
        Case_Speak_FailureLog();
        Case_Recover_After_Authorized();
        Case_Handshake_NotRepeated();
        Case_Handshake_Retry_NotSpammed();
        Case_Stop();
        Case_Braille_Export_Presence();
        Case_VersionMismatch_FallsThrough();
        Case_VersionMismatch_AllCandidates();
        Case_RegistryLookup();

        Console.WriteLine("### B. 按键描述解析（Hotkey）");
        Case_Hotkey_Parse();

        Console.WriteLine();
        Console.WriteLine(string.Format("结果: {0} 通过, {1} 失败", _pass, _fail));
        return _fail == 0 ? 0 : 1;
    }

    private static void Prepare(string dir, string sourceName)
    {
        Directory.CreateDirectory(dir);
        string from = Path.Combine(_root, sourceName);
        if (!File.Exists(from)) throw new FileNotFoundException("找不到桩 DLL（应由 run.ps1 先构建）: " + from);
        File.Copy(from, Path.Combine(dir, "ZDSRAPI_x64.dll"), true);
    }

    // ---------------------------------------------------------------- A. Zdsr

    private static void Case_MissingDll()
    {
        Begin("DLL 不在（大多数玩家的机器）：判不可用，且给出可读原因");
        UseEmpty();
        Env("ZDSR_STUB_STATE", "4");

        bool ok = A11yFramework.Zdsr.TestAvailable();

        Check("TestAvailable() == false", !ok);
        Check("DllLoaded == false", !A11yFramework.Zdsr.DllLoaded);
        Check("LastError 提到「没有找到」", Contains(A11yFramework.Zdsr.LastError, "没有找到"));
        Check("LastError 带上要用的文件名", Contains(A11yFramework.Zdsr.LastError, "ZDSRAPI_x64.dll"));
        Check("Speak() 不抛异常且返回 false", !A11yFramework.Zdsr.Speak("你好", true));
        End();
    }

    private static void Case_NotAuthorized()
    {
        Begin("DLL 在、读屏没运行/未授权（GetSpeakState=2，公益档）：判不可用");
        UseStub();
        Env("ZDSR_STUB_STATE", "2");

        bool ok = A11yFramework.Zdsr.TestAvailable();

        Check("TestAvailable() == false", !ok);
        Check("DllLoaded == true（DLL 本身是好的）", A11yFramework.Zdsr.DllLoaded);
        Check("State == 2", A11yFramework.Zdsr.State == 2);
        Check("LastError 说明是未授权/没运行", Contains(A11yFramework.Zdsr.LastError, "未授权")
              || Contains(A11yFramework.Zdsr.LastError, "没有运行"));

        // 关键：未授权时 Speak 也可能返回 0 —— 判据绝不能是它
        ClearLog();
        Env("ZDSR_STUB_SPEAKRC", "0");
        bool spoke = A11yFramework.Zdsr.Speak("未授权也不能算成功", true);
        Check("Speak() 即使桩返回 0 也判失败（不靠返回值判可用性）", false == spoke);
        End();
    }

    private static void Case_Available_Idle()
    {
        Begin("GetSpeakState=4（空闲）：判可用");
        UseStub();
        Env("ZDSR_STUB_STATE", "4");

        Check("TestAvailable() == true", A11yFramework.Zdsr.TestAvailable());
        Check("State == 4", A11yFramework.Zdsr.State == 4);
        Check("LoadedFrom 指向桩 DLL", string.Equals(A11yFramework.Zdsr.LoadedFrom, _dllPath, StringComparison.OrdinalIgnoreCase));
        Check("HasBrailleExport == true（这个构建带 Braille）", A11yFramework.Zdsr.HasBrailleExport);
        End();
    }

    private static void Case_Available_Speaking()
    {
        Begin("GetSpeakState=3（正在朗读）：也判可用");
        UseStub();
        Env("ZDSR_STUB_STATE", "3");
        Check("TestAvailable() == true", A11yFramework.Zdsr.TestAvailable());
        Check("State == 3", A11yFramework.Zdsr.State == 3);
        End();
    }

    private static void Case_Speak_Parameters()
    {
        Begin("参数逐个回显校验：InitTTS(0,NULL,false) / Speak(文本,interrupt)");
        UseStub();
        Env("ZDSR_STUB_STATE", "4");
        Env("ZDSR_STUB_SPEAKRC", "0");
        ClearLog();                       // 清在 TestAvailable 之前：InitTTS 就在那一步发生
        A11yFramework.Zdsr.TestAvailable();
        bool a = A11yFramework.Zdsr.Speak("【 角色名 】测试文本，含全角标点。", false);
        bool b = A11yFramework.Zdsr.Speak("第 1 个 选项", true);
        Thread.Sleep(50);

        string log = ReadLog();
        Check("首次 Speak 返回成功", a);
        Check("第二次 Speak 返回成功", b);
        Check("InitTTS 的 type=0（读屏通道）", Contains(log, "InitTTS:type=0"));
        Check("InitTTS 的 keyDownInterrupt=0（按键不打断，否则推进键会掐断台词）", Contains(log, "keyDownInterrupt=0"));
        Check("InitTTS 的 channelName 传的是 NULL", Contains(log, "channel=<NULL>"));
        Check("中文与全角标点原样送达（UTF-16 → LPWStr）", Contains(log, "Speak:text=【 角色名 】测试文本，含全角标点。"));
        Check("排队朗读 interrupt=0", Contains(log, "Speak:interrupt=0"));
        Check("打断朗读 interrupt=1", Contains(log, "Speak:interrupt=1"));
        Check("两句都在日志里", CountOccurrences(log, "Speak:interrupt") == 2);
        End();
    }

    private static void Case_Speak_FailureLog()
    {
        Begin("Speak 失败（返回 2）：报出原因，不静默");
        UseStub();
        Env("ZDSR_STUB_STATE", "4");
        Env("ZDSR_STUB_SPEAKRC", "2");
        A11yFramework.Zdsr.TestAvailable();

        bool ok = A11yFramework.Zdsr.Speak("这句话送不出去", true);
        Check("Speak() == false", !ok);
        Check("LastError 解释了返回码 2", Contains(A11yFramework.Zdsr.LastError, "2"));
        End();
    }

    private static void Case_Recover_After_Authorized()
    {
        Begin("掉线后恢复：未授权 → 5 秒门禁 → 授权恢复 → 重新判为可用");
        UseStub();
        Env("ZDSR_STUB_STATE", "2");
        Check("第一轮：不可用", !A11yFramework.Zdsr.TestAvailable());

        // 模拟「用户买/插了狗」——桩 DLL 每次都读环境变量，所以改一下就生效
        Env("ZDSR_STUB_STATE", "4");
        // 握手门禁（5 秒）内不重复握手：Speech 的重试是 10 秒一次，所以这里如实等一次门禁
        Check("门禁期内不重复握手（仍判不可用）", !A11yFramework.Zdsr.TestAvailable());
        Thread.Sleep(5200);
        Check("门禁过后：恢复可用", A11yFramework.Zdsr.TestAvailable());
        Check("State 跟到 4", A11yFramework.Zdsr.State == 4);
        End();
    }

    private static void Case_Handshake_NotRepeated()
    {
        Begin("握手不刷屏：连续判定可用时不重复 InitTTS");
        UseStub();
        Env("ZDSR_STUB_STATE", "4");
        ClearLog();

        for (int i = 0; i < 5; i++) A11yFramework.Zdsr.TestAvailable();
        Thread.Sleep(50);

        string log = ReadLog();
        Check("InitTTS 只调了 1 次（5 次判定）", CountOccurrences(log, "InitTTS:") == 1);
        Check("GetSpeakState 调了 5 次（每次判定一次）", CountOccurrences(log, "GetSpeakState:") == 5);
        End();
    }

    private static void Case_Handshake_Retry_NotSpammed()
    {
        Begin("未授权期间连说三句：握手一次、状态查一次、**一句都不往读屏送**");
        UseStub();
        Env("ZDSR_STUB_STATE", "2");
        Env("ZDSR_STUB_SPEAKRC", "0");   // 桩故意回 0：模拟官方那个「未授权也返回成功」
        ClearLog();

        for (int i = 0; i < 3; i++) A11yFramework.Zdsr.Speak("第 " + (i + 1) + " 句", false);
        Thread.Sleep(50);

        string log = ReadLog();
        Check("InitTTS 只调了 1 次（不是每句都握手）", CountOccurrences(log, "InitTTS:") == 1);
        Check("GetSpeakState 只查了 1 次（5 秒缓存）", CountOccurrences(log, "GetSpeakState:") == 1);
        Check("未授权时不往读屏送文本，Speak 桩调用 0 次", CountOccurrences(log, "Speak:interrupt") == 0);
        End();
    }

    private static void Case_Stop()
    {
        Begin("Stop() 走 StopSpeak");
        UseStub();
        Env("ZDSR_STUB_STATE", "3");
        A11yFramework.Zdsr.TestAvailable();
        ClearLog();
        bool ok = A11yFramework.Zdsr.Stop();
        Thread.Sleep(50);
        Check("Stop() == true", ok);
        Check("桩收到 StopSpeak", Contains(ReadLog(), "StopSpeak"));
        End();
    }

    private static void Case_Braille_Export_Presence()
    {
        Begin("Braille 导出：新构建有 / 旧构建（1.0.0.1）没有也不报错");
        UseStub();
        Env("ZDSR_STUB_STATE", "4");
        Env("ZDSR_STUB_BRAILLERC", "0");
        A11yFramework.Zdsr.TestAvailable();
        ClearLog();
        Check("带 Braille 的构建：HasBrailleExport == true", A11yFramework.Zdsr.HasBrailleExport);
        Check("Braille() 发送成功", A11yFramework.Zdsr.Braille("测试", false));
        Thread.Sleep(50);
        Check("桩收到 Braille:text=测试", Contains(ReadLog(), "Braille:text=测试"));

        // 换成没有 Braille 导出的旧版构建
        UseStubNoBraille();
        Check("旧构建：DLL 仍可用", A11yFramework.Zdsr.TestAvailable());
        Check("旧构建：HasBrailleExport == false", !A11yFramework.Zdsr.HasBrailleExport);
        Check("旧构建：Braille() 返回 false 而不是抛异常", !A11yFramework.Zdsr.Braille("测试", false));
        End();
    }

    // ------------------------------------------------ A2. 版本不匹配就换下一份

    private static void Case_VersionMismatch_FallsThrough()
    {
        Begin("包内那份 dll 太旧（InitTTS=1）⇒ 自动换下一份候选，而不是判死");
        Env("ZDSR_STUB_STATE", "4");
        Env("ZDSR_STUB_INITRC", "0");
        // 第一份是「版本不匹配」的桩，第二份是正常桩：应当落到第二份
        UseDirs(_stubMismatchDir + ";" + _stubDir);

        bool ok = A11yFramework.Zdsr.TestAvailable();
        Check("TestAvailable() == true（换到了第二份）", ok);
        Check("LoadedFrom 指向第二份（正常的那份）",
              string.Equals(A11yFramework.Zdsr.LoadedFrom, _dllPath, StringComparison.OrdinalIgnoreCase));
        Check("DllLoaded == true", A11yFramework.Zdsr.DllLoaded);
        End();
    }

    private static void Case_VersionMismatch_AllCandidates()
    {
        Begin("所有候选都版本不匹配 ⇒ 判不可用，且原因写明版本不匹配");
        Env("ZDSR_STUB_STATE", "4");
        UseDirs(_stubMismatchDir);

        bool ok = A11yFramework.Zdsr.TestAvailable();
        Check("TestAvailable() == false", !ok);
        Check("LastError 提到版本不匹配", Contains(A11yFramework.Zdsr.LastError, "版本不匹配"));
        Check("Speak() 返回 false 且不抛异常", !A11yFramework.Zdsr.Speak("你好", true));
        End();
    }

    private static void Case_RegistryLookup()
    {
        Begin("注册表查找争渡安装目录（装在非默认盘的用户靠它自动找到）");
        var dirs = A11yFramework.Zdsr.RegistryInstallDirs();
        Console.WriteLine("    注册表里找到 " + dirs.Count + " 条：" +
                          (dirs.Count > 0 ? string.Join(" | ", dirs.ToArray()) : "(无)"));

        // 本机装了争渡（HKLM 卸载项里有 DisplayName=争渡读屏、InstallLocation 指向安装目录），
        // 所以这里断言「找得到且指向真实安装目录」。注册表里没有就只打印、不判失败 ——
        // 这条用例是集成检查，不该让别的机器上的自检变红。
        string known = @"C:\Program Files (x86)\zdsr\zdsr";
        if (Directory.Exists(known))
        {
            bool hit = false;
            foreach (string d in dirs)
            {
                if (string.Equals(d.TrimEnd('\\'), known, StringComparison.OrdinalIgnoreCase)) { hit = true; break; }
            }
            Check(@"注册表里找得到 " + known, hit);
        }
        else
        {
            Console.WriteLine("    （本机没有默认安装目录，跳过断言）");
        }
        End();
    }

    // ---------------------------------------------------------------- B. Hotkey
    /// <summary>自检用的扁平解析结果（Hotkey.Spec 是 internal 结构体，同程序集可直接用）。</summary>
    private struct Hk { public bool Ok; public string Key; public bool Alt, Ctrl, Shift; public string Why; }

    private static Hk HkParse(string spec)
    {
        A11yFramework.Hotkey.Spec s;
        string why;
        bool ok = A11yFramework.Hotkey.Parse(spec, out s, out why);
        var r = new Hk();
        r.Ok = ok;
        r.Key = ok ? s.Key.ToString() : "";
        r.Alt = s.Alt; r.Ctrl = s.Ctrl; r.Shift = s.Shift;
        r.Why = why ?? "";
        return r;
    }

    private static void Case_Hotkey_Parse()
    {
        Begin("按键描述解析：单键 / 修饰键 / 冲突避让写法 / 各种写错都要有原因");

        Hk r;

        r = HkParse("F9");
        Check("「F9」能解析且主键是 F9", r.Ok && r.Key == "F9");
        Check("「F9」不带任何修饰键", r.Ok && !r.Alt && !r.Ctrl && !r.Shift);

        r = HkParse("f9");
        Check("大小写不敏感（f9）", r.Ok && r.Key == "F9");

        r = HkParse("  Backspace  ");
        Check("两端空格容忍（Backspace）", r.Ok && r.Key == "Backspace");

        r = HkParse("Alt+Shift+F9");
        Check("冲突避让写法「Alt+Shift+F9」能解析", r.Ok && r.Key == "F9");
        Check("「Alt+Shift+F9」的 Alt 生效", r.Ok && r.Alt);
        Check("「Alt+Shift+F9」的 Shift 生效", r.Ok && r.Shift);
        Check("「Alt+Shift+F9」没有 Ctrl", r.Ok && !r.Ctrl);

        r = HkParse("LeftAlt+F9");
        Check("「LeftAlt+F9」解析成功（左右两侧都按 Alt 处理）", r.Ok && r.Alt);

        r = HkParse("Ctrl+Alt+Backspace");
        Check("「Ctrl+Alt+Backspace」解析成功且 Ctrl/Alt 都生效", r.Ok && r.Ctrl && r.Alt);
        Check("「Ctrl+Alt+Backspace」主键是 Backspace", r.Ok && r.Key == "Backspace");

        r = HkParse("");
        Check("空配置=停用，且原因写明是留空", !r.Ok && Contains(r.Why, "留空"));

        // 流水线 G3：Enum.TryParse("0") 返回 true 但得到 KeyCode.None —— 必须拒绝
        r = HkParse("0");
        Check("「0」被拒绝（G3：TryParse(\"0\") 会成功但得到 None）", !r.Ok);
        Check("「0」的原因提到纯数字", Contains(r.Why, "纯数字"));

        r = HkParse("48");
        Check("「48」被拒绝（同上）", !r.Ok && Contains(r.Why, "纯数字"));

        r = HkParse("Foo");
        Check("乱写的键名被拒绝且原因可读", !r.Ok && Contains(r.Why, "不认识"));

        r = HkParse("Alt");
        Check("只写修饰键被拒绝", !r.Ok && Contains(r.Why, "修饰键"));

        r = HkParse("Alt+Shift");
        Check("只写多个修饰键也被拒绝", !r.Ok && Contains(r.Why, "修饰键"));

        r = HkParse("F9+Backspace");
        Check("写了两个主键被拒绝", !r.Ok && Contains(r.Why, "多个主键"));

        r = HkParse("None");
        Check("「None」被拒绝（不能把功能键设成「无键」）", !r.Ok);
        End();
    }

    // ---------------------------------------------------------------- 基础设施

    private static void Begin(string title) { Console.WriteLine(); Console.WriteLine("---- " + title); }
    private static void End() { }

    private static void Check(string what, bool ok)
    {
        if (ok) { _pass++; Console.WriteLine("  ok   " + what); }
        else { _fail++; Console.WriteLine("  FAIL " + what); }
    }

    private static void Env(string name, string value) { Environment.SetEnvironmentVariable(name, value); }

    /// <summary>把 Zdsr 的搜索范围钉在某个目录上（Zdsr 认 A11Y_ZDSR_DIR，见其注释）。</summary>
    private static void UseDir(string dir) { UseDirs(dir); }

    /// <summary>多个目录用 ';' 分隔 —— 用来验证「这一份版本不匹配就换下一份」。</summary>
    private static void UseDirs(string spec)
    {
        Environment.SetEnvironmentVariable("A11Y_ZDSR_DIR", spec);
        Environment.SetEnvironmentVariable("ZDSR_STUB_LOG", _logPath);
        _dllPath = Path.Combine(spec.Split(';')[spec.Split(';').Length - 1], "ZDSRAPI_x64.dll");
        A11yFramework.Zdsr.Reset();
    }

    private static void UseEmpty() { UseDir(_emptyDir); }
    private static void UseStub() { UseDir(_stubDir); }
    private static void UseStubNoBraille() { UseDir(_stubNoBrailleDir); }

    private static void ClearLog()
    {
        try { if (File.Exists(_logPath)) File.Delete(_logPath); } catch { }
    }

    private static string ReadLog()
    {
        try { return File.Exists(_logPath) ? File.ReadAllText(_logPath, Encoding.UTF8) : ""; }
        catch { return ""; }
    }

    private static bool Contains(string haystack, string needle)
    {
        return haystack != null && haystack.Contains(needle);
    }

    private static int CountOccurrences(string haystack, string needle)
    {
        if (string.IsNullOrEmpty(haystack)) return 0;
        int n = 0, i = 0;
        while ((i = haystack.IndexOf(needle, i, StringComparison.Ordinal)) >= 0) { n++; i += needle.Length; }
        return n;
    }
}
