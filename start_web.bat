@echo off
cd /d "%~dp0"

echo.
echo ====================================
echo   SFG/SRS Web GUI Control Panel
echo ====================================
echo.

REM Use Anaconda py310 environment directly (avoids conda activate issues in bat)
set "PATH=C:\ProgramData\anaconda3\envs\py310;C:\ProgramData\anaconda3\envs\py310\Scripts;C:\ProgramData\anaconda3\envs\py310\Library\bin;%PATH%"
set "PYTHON_EXE=C:\ProgramData\anaconda3\envs\py310\python.exe"

REM Quick check: if uvicorn is missing, install all dependencies now
%PYTHON_EXE% -c "import uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies, please wait...
    %PYTHON_EXE% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] pip install failed. Check your internet connection.
        echo [ERROR] You can also run manually:
        echo         %PYTHON_EXE% -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Starting server...
echo [INFO] URL: http://localhost:8081
echo.

%PYTHON_EXE% -m uvicorn web.app:app --host 0.0.0.0 --port 8081

pause
