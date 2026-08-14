@echo off
setlocal
cd /d "%~dp0"

if not defined ANTHROPIC_API_KEY (
    echo ERROR: ANTHROPIC_API_KEY is not set for this process/user.
    echo Set it once with:  setx ANTHROPIC_API_KEY "sk-ant-..."
    echo then open a new session ^(or set it directly on the Task Scheduler action^).
    exit /b 1
)

python -m pip install --quiet --upgrade anthropic >nul 2>&1

python "%~dp0news_briefing.py" >> "%~dp0news_briefing.log" 2>&1
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% neq 0 (
    echo %DATE% %TIME% - news_briefing.py failed with exit code %EXITCODE% >> "%~dp0news_briefing.log"
)

exit /b %EXITCODE%
