@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%blackboard_day5_7"
set "FRONTEND_DIR=%ROOT%interview-assistant-stage4-whisper"
set "BACKEND_CONDA_ENV=chuangxin"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=54321"

cd /d "%ROOT%"

echo =========================
echo Atlas Interview local launcher
echo =========================
echo Project root: %ROOT%
echo Backend conda env: %BACKEND_CONDA_ENV%

call :check_dir "%BACKEND_DIR%" "Backend"
if errorlevel 1 goto :done

call :check_dir "%FRONTEND_DIR%" "Frontend"
if errorlevel 1 goto :done

call :is_port_listening %BACKEND_PORT%
if errorlevel 1 (
    echo Starting backend on port %BACKEND_PORT%...
    start "Atlas Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && conda run -n %BACKEND_CONDA_ENV% python -m uvicorn orchestrator_v0:app --reload --host 127.0.0.1 --port %BACKEND_PORT%"
) else (
    echo Backend already running on port %BACKEND_PORT%.
)

timeout /t 3 /nobreak >nul

call :is_port_listening %FRONTEND_PORT%
if errorlevel 1 (
    echo Starting frontend on port %FRONTEND_PORT%...
    start "Atlas Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && npm run dev"
) else (
    echo Frontend already running on port %FRONTEND_PORT%.
)

echo =========================
echo Done.
echo Backend:  http://127.0.0.1:%BACKEND_PORT%
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo =========================

:done
endlocal
exit /b

:check_dir
if not exist "%~1" (
    echo %~2 directory not found:
    echo %~1
    exit /b 1
)
exit /b 0

:is_port_listening
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %1 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
exit /b %errorlevel%
