@echo off
REM 이 PC에서 딱 한 번만 실행하면 진짜 실행파일(.exe)이 만들어집니다.
REM 인터넷이 되는 PC에서 실행해야 합니다(PyInstaller 설치 때문).
cd /d "%~dp0"

echo PyInstaller 설치 중...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo pip 설치에 실패했습니다. 파이썬이 설치되어 있고 인터넷이 되는지 확인하세요.
    pause
    exit /b 1
)

echo.
echo 실행파일 만드는 중...
python -m PyInstaller --onefile --noconsole --name "유상사급자동화" gui.pyw

echo.
echo ============================================
echo 완료되면 dist\유상사급자동화.exe 가 생성됩니다.
echo 이 exe 파일만 복사해서 다른 폴더/다른 PC로 옮겨도
echo (같은 Windows 계열이면) 파이썬 설치 없이 바로 실행됩니다.
echo ============================================
pause
