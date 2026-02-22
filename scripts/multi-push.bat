@echo off
setlocal enabledelayedexpansion

echo 🚀 开始多远程仓库推送...

REM 检查Git状态
git status --porcelain > nul
if %errorlevel% equ 0 (
    echo ✅ 工作目录干净，准备推送
) else (
    echo ⚠️  工作目录有未提交的更改，请先提交或暂存
    git status --short
    set /p confirm=是否继续推送? (y/N): 
    if /i not "!confirm!"=="y" (
        exit /b 1
    )
)

REM 获取当前分支
for /f %%i in ('git rev-parse --abbrev-ref HEAD') do set CURRENT_BRANCH=%%i
echo 📋 当前分支: %CURRENT_BRANCH%

REM 检查远程仓库配置
echo 🔍 检查远程仓库配置...
git remote -v

REM 推送到GitHub
echo 📤 正在推送到GitHub...
git push origin %CURRENT_BRANCH%
if %errorlevel% equ 0 (
    echo ✅ GitHub推送成功
) else (
    echo ❌ GitHub推送失败
    exit /b 1
)

REM 推送到Gitee
echo 📤 正在推送到Gitee...
git push gitee %CURRENT_BRANCH%
if %errorlevel% equ 0 (
    echo ✅ Gitee推送成功
) else (
    echo ❌ Gitee推送失败
    exit /b 1
)

echo 🎉 所有推送完成！
echo 📊 推送状态:
for /f %%i in ('git rev-parse HEAD') do set COMMIT_HASH=%%i
echo   - GitHub: %COMMIT_HASH%
echo   - Gitee:  %COMMIT_HASH%

pause
