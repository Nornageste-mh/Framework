/*
 * 争渡读屏 API（ZDSRAPI）的**桩 DLL** —— 只用于 A11yFramework 的机械自检。
 *
 * 它按官方头文件的签名实现五个导出，把每次调用**原样记进一个日志文件**，
 * 并从环境变量里取返回值。这样自检程序就能断言：
 *   · 我们的委托签名/字符集/调用约定有没有把参数送错（文本、NULL、BOOL 都回显）
 *   · 可用性判据是不是 GetSpeakState（而不是 Speak 的返回值）
 *   · 失败之后的重试、握手次数、恢复路径是否按预期走
 *
 * 构建（w64devkit / MinGW-w64，x64）：
 *     gcc -shared -O2 -o zdsr_stub.dll zdsr_stub.c
 * 不定义 ZDSR_STUB_NO_BRAILLE 时带 Braille 导出（对应 1.0.0.5+）；
 * 定义它则只有四个导出（对应 1.0.0.1）。
 *
 * 环境变量：
 *     ZDSR_STUB_LOG        日志文件路径（UTF-8，每行一次调用）；未设则不记
 *     ZDSR_STUB_STATE      GetSpeakState 的返回值，默认 4
 *     ZDSR_STUB_INITRC     InitTTS 的返回值，默认 0
 *     ZDSR_STUB_SPEAKRC    Speak 的返回值，默认 0
 *     ZDSR_STUB_BRAILLERC  Braille 的返回值，默认 0
 *
 * 【注意】这不是争渡读屏的一部分，也**不得**随任何发布包分发。
 */

#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPORT __declspec(dllexport) __stdcall

static void stub_log(const char *fmt, ...)
{
    char path[MAX_PATH];
    DWORD n = GetEnvironmentVariableA("ZDSR_STUB_LOG", path, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return;

    FILE *f = fopen(path, "ab");
    if (!f) return;

    va_list ap;
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
    fputc('\n', f);
    fclose(f);
}

static int env_int(const char *name, int dflt)
{
    char buf[32];
    DWORD n = GetEnvironmentVariableA(name, buf, sizeof(buf));
    if (n == 0 || n >= sizeof(buf)) return dflt;
    return atoi(buf);
}

/* 把 UTF-16 文本转成 UTF-8 写进日志；NULL 写 <NULL>。 */
static void log_text(const char *tag, const wchar_t *w)
{
    if (w == NULL) { stub_log("%s=<NULL>", tag); return; }

    int need = WideCharToMultiByte(CP_UTF8, 0, w, -1, NULL, 0, NULL, NULL);
    if (need <= 0) { stub_log("%s=<CONVFAIL>", tag); return; }

    char *buf = (char *)malloc((size_t)need + 1);
    if (!buf) { stub_log("%s=<OOM>", tag); return; }
    WideCharToMultiByte(CP_UTF8, 0, w, -1, buf, need, NULL, NULL);
    stub_log("%s=%s", tag, buf);
    free(buf);
}

EXPORT int InitTTS(int type, const wchar_t *channelName, int bKeyDownInterrupt)
{
    stub_log("InitTTS:type=%d keyDownInterrupt=%d channel=%s",
             type, bKeyDownInterrupt ? 1 : 0,
             channelName == NULL ? "<NULL>" : "<NOT-NULL>");
    return env_int("ZDSR_STUB_INITRC", 0);
}

EXPORT int Speak(const wchar_t *text, int bInterrupt)
{
    stub_log("Speak:interrupt=%d", bInterrupt ? 1 : 0);
    log_text("Speak:text", text);
    return env_int("ZDSR_STUB_SPEAKRC", 0);
}

EXPORT int GetSpeakState(void)
{
    int st = env_int("ZDSR_STUB_STATE", 4);
    stub_log("GetSpeakState:ret=%d", st);
    return st;
}

EXPORT void StopSpeak(void)
{
    stub_log("StopSpeak");
}

#ifndef ZDSR_STUB_NO_BRAILLE
EXPORT int Braille(const wchar_t *text, int bFlashMessage)
{
    stub_log("Braille:flash=%d", bFlashMessage ? 1 : 0);
    log_text("Braille:text", text);
    return env_int("ZDSR_STUB_BRAILLERC", 0);
}
#endif
