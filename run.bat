@echo off
setlocal
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "ACTIVATE_BAT=%VENV_DIR%\Scripts\activate.bat"
set "PYTHON_CMD=python"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
)

if not exist "%ACTIVATE_BAT%" (
    echo [INFO] 首次运行，正在创建虚拟环境 %VENV_DIR% ...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败，请确认 Python 已正确安装。
        pause
        exit /b 1
    )

    call "%ACTIVATE_BAT%"
    if errorlevel 1 (
        echo [ERROR] 激活虚拟环境失败。
        pause
        exit /b 1
    )

    echo [INFO] 正在安装依赖 ...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败，请检查网络或 requirements.txt。
        pause
        exit /b 1
    )
) else (
    echo [INFO] 检测到已有虚拟环境，正在激活 ...
    call "%ACTIVATE_BAT%"
    if errorlevel 1 (
        echo [ERROR] 激活虚拟环境失败。
        pause
        exit /b 1
    )
)

echo [INFO] 启动爬虫 ...
python crawler.py %*
set "EXIT_CODE=%errorlevel%"

echo.
if %EXIT_CODE%==0 (
    echo [INFO] 脚本执行完成。
) else (
    echo [WARN] 脚本异常退出，退出码：%EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
