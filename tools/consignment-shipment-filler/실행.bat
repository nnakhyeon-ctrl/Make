@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw gui.pyw
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python gui.pyw
    ) else (
        echo 파이썬이 설치되어 있지 않습니다. python.org 에서 설치한 뒤 다시 실행하세요.
        pause
    )
)
