# 一键推送博客到 GitHub
# 用法: .\push.ps1 "提交信息"  (不带参数用默认信息)

param(
    [string]$Message = "update blog $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

Write-Host "==> 1/4 检查改动..." -ForegroundColor Cyan
git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "没有任何改动，无需推送。" -ForegroundColor Yellow
    exit 0
}
Write-Host "改动文件:"
$staged | ForEach-Object { Write-Host "  $_" }

Write-Host "==> 2/4 提交: $Message" -ForegroundColor Cyan
git commit -m $Message

Write-Host "==> 3/4 同步远程..." -ForegroundColor Cyan
# 拉取远程更新；若有冲突，一律以本地版本为准
git pull origin main --no-edit -X ours
if ($LASTEXITCODE -ne 0) {
    Write-Host "拉取远程失败，请检查网络或认证。" -ForegroundColor Red
    exit 1
}

Write-Host "==> 4/4 推送到 GitHub..." -ForegroundColor Cyan
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "推送失败，请检查网络或 GitHub 认证。" -ForegroundColor Red
    exit 1
}

Write-Host "完成! 已推送到 https://github.com/tanxue0118/blog" -ForegroundColor Green
