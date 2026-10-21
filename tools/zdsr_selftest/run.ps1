#Requires -Version 5.1
<#
    A11yFramework 平台层的机械自检：platform\Zdsr.cs（争渡后端）+ platform\Hotkey.cs（按键解析）。

    三步：
      1/3 用 gcc 编三个桩 DLL（带/不带 Braille 导出；第三种 InitTTS 固定返回 1）
      2/3 dotnet build 自检程序（它直接编译 platform 里那两个文件）
      3/3 跑用例（71 条）：DLL 缺失 / 未授权 / 可用 / 参数回显 / 掉线恢复 / 不刷屏 / Stop /
                   Braille / 旧 dll 自动跳过 / 注册表查找
                   + 按键描述解析（含 G3 那个「纯数字得到 KeyCode.None」的坑）

    为什么值得有这一步：争渡的授权位无法在开发机上稳定复现，而这一级的错全都
    出在「看不见的路径」上（签名送错、DLL 不在、未授权时 Speak 仍返回 0）。
    桩 DLL 把这些状态全部造出来，于是这些路径变成可机械断言的。

    用法：
        .\tools\zdsr_selftest\run.ps1
        .\tools\zdsr_selftest\run.ps1 -Keep                        # 保留 bin\（看日志与桩 DLL）
        .\tools\zdsr_selftest\run.ps1 -GameDir "C:\Program Files (x86)\Steam\steamapps\common\<游戏目录>"

    注意：本脚本必须存为 UTF-8 **带 BOM**（PS 5.1 读无 BOM 脚本会按 GBK 解码并语法错误）。
#>
[CmdletBinding()]
param(
    [string]$Gcc = "$env:A11Y_GCC",
    # 借一个已安装的游戏取 UnityEngine.CoreModule.dll（Hotkey.cs 只用它的 KeyCode 枚举）。
    # 不给 -GameDir 时读环境变量 A11Y_GAME_DIR（指向游戏根目录）。
    [string]$GameDir = "$env:A11Y_GAME_DIR",
    [switch]$Keep
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$out = Join-Path $here "bin"

function Fail($msg) { Write-Host ""; Write-Host "FAIL  $msg" -ForegroundColor Red; exit 1 }
function Ok($msg) { Write-Host "  ok  $msg" -ForegroundColor Green }

if ([string]::IsNullOrEmpty($GameDir)) {
    Fail "需要游戏目录：用 -GameDir 指定，或设环境变量 A11Y_GAME_DIR（只需要其中的 *_Data\Managed\UnityEngine.CoreModule.dll）"
}

Write-Host ""
Write-Host "=== A11yFramework 平台层自检（Zdsr.cs / Hotkey.cs）===" -ForegroundColor Cyan

# ---------------------------------------------------------------- 1/3 桩 DLL
Write-Host ""
Write-Host "[1/3] 编桩 DLL（gcc）" -ForegroundColor Cyan

if ([string]::IsNullOrEmpty($Gcc)) {
    $cmd = Get-Command gcc -ErrorAction SilentlyContinue
    if ($cmd) { $Gcc = $cmd.Source }
}
if ([string]::IsNullOrEmpty($Gcc) -or -not (Test-Path $Gcc)) {
    Fail "找不到 gcc：装一个 MinGW-w64（w64devkit 即可）并加进 PATH，或用 -Gcc / 环境变量 A11Y_GCC 指定 gcc.exe"
}
Ok "gcc: $Gcc"

if (-not (Test-Path $out)) { New-Item -ItemType Directory -Force -Path $out | Out-Null }
$src = Join-Path $here "zdsr_stub.c"
if (-not (Test-Path $src)) { Fail "找不到 $src" }

& $Gcc -shared -O2 -o (Join-Path $out "zdsr_stub.dll") $src 2>&1 | ForEach-Object { Write-Host "      $_" }
if ($LASTEXITCODE -ne 0) { Fail "桩 DLL（带 Braille）编译失败" }

& $Gcc -shared -O2 -DZDSR_STUB_NO_BRAILLE -o (Join-Path $out "zdsr_stub_nobraille.dll") $src 2>&1 | ForEach-Object { Write-Host "      $_" }
if ($LASTEXITCODE -ne 0) { Fail "桩 DLL（不带 Braille）编译失败" }

# 第三份：InitTTS 固定返回 1（版本不匹配）—— 用来验证「这一份太旧就自动换下一份候选」
& $Gcc -shared -O2 -DZDSR_STUB_FORCE_INITRC=1 -o (Join-Path $out "zdsr_stub_initmismatch.dll") $src 2>&1 | ForEach-Object { Write-Host "      $_" }
if ($LASTEXITCODE -ne 0) { Fail "桩 DLL（版本不匹配）编译失败" }
Ok "三个桩 DLL 已生成"

# ---------------------------------------------------------------- 2/3 自检程序
Write-Host ""
Write-Host "[2/3] dotnet build 自检程序" -ForegroundColor Cyan

$managed = Get-ChildItem -LiteralPath $GameDir -Directory -Filter "*_Data" -ErrorAction SilentlyContinue |
           ForEach-Object { Join-Path $_.FullName "Managed" } |
           Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $managed) { Fail "在 $GameDir 下找不到 *_Data\Managed（用 -GameDir 指定）" }
if (-not (Test-Path (Join-Path $managed "UnityEngine.CoreModule.dll"))) {
    Fail "缺少 $(Join-Path $managed 'UnityEngine.CoreModule.dll')"
}
Ok "UnityEngine: $managed"

Push-Location $here
try {
    & dotnet build (Join-Path $here "ZdsrSelfTest.csproj") -c Release -v minimal --nologo -o $out `
        -p:UnityManaged="$managed" 2>&1 | ForEach-Object { Write-Host "      $_" }
    $code = $LASTEXITCODE
} finally { Pop-Location }
if ($code -ne 0) { Fail "自检程序编译失败" }
Ok "编译通过"

foreach ($n in @("zdsr_stub.dll", "zdsr_stub_nobraille.dll", "zdsr_stub_initmismatch.dll")) {
    $from = Join-Path $out $n
    if (-not (Test-Path $from)) { Fail "缺 $from" }
}

# ---------------------------------------------------------------- 3/3 跑用例
Write-Host ""
Write-Host "[3/3] 跑用例" -ForegroundColor Cyan
$exe = Join-Path $out "ZdsrSelfTest.exe"
if (-not (Test-Path $exe)) { Fail "找不到 $exe" }
& $exe $out
$code = $LASTEXITCODE

Write-Host ""
if ($code -ne 0) { Fail "有用例失败（上面 FAIL 行）" }
Write-Host "PASS  平台层的选路、失败路径、参数传递与按键解析都符合预期。" -ForegroundColor Green
Write-Host "      注意：这证明的是「代码按设计工作」，不是「争渡真的念出来了」——" -ForegroundColor Yellow
Write-Host "      后者需要商业版/青春版授权 + 实机（见 CHANGELOG 的实测章节）。" -ForegroundColor Yellow
Write-Host ""

if (-not $Keep) { Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue }
