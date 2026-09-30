@echo off
cd /d "%~dp0"
title Blog Push

rem Double-click to push with timestamp message
rem Or run: push.bat "your message"

set "MSG=%~1"
if "%MSG%"=="" set "MSG=update blog %date:~0,4%-%date:~5,2%-%date:~8,2% %time:~0,5%"

echo ==========================================
echo   Blog one-click push
echo ==========================================
echo.

echo [1/5] Generating static post pages...
py generate.py
if errorlevel 1 (
    echo.
    echo [FAIL] generate.py error! Check Python and data.json.
    pause
    exit /b 1
)
echo.

echo [2/5] Checking changes...
git add -A
git diff --cached --quiet
if %errorlevel%==0 (
    echo.
    echo Nothing to push. No changes found.
    echo.
    pause
    exit /b 0
)
git diff --cached --name-status
echo.

echo [3/5] Commit: %MSG%
git commit -m "%MSG%"
if errorlevel 1 (
    echo.
    echo [FAIL] Commit error!
    pause
    exit /b 1
)
echo.

echo [4/5] Syncing remote...
git pull origin main --no-edit -X ours
if errorlevel 1 (
    echo.
    echo [FAIL] Pull failed, check network!
    pause
    exit /b 1
)
echo.

echo [5/5] Pushing to GitHub...
git push origin main
if errorlevel 1 (
    echo.
    echo [FAIL] Push failed, check network or credentials!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Done! Pushed to GitHub
echo   https://github.com/tanxue0118/blog
echo ==========================================
echo.
pause
