@echo off
setlocal

set "BACKEND_DIR=C:\Users\hp\Desktop\blackboard_day5_7"
set "FRONTEND_DIR=C:\Users\hp\Desktop\interview-assistant-stage4-whisper"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=54321"

echo =========================
echo Atlas local launcher
echo =========================

call :check_dir "%BACKEND_DIR%" "Backend"
if errorlevel 1 goto :done

call :check_dir "%FRONTEND_DIR%" "Frontend"
if errorlevel 1 goto :done

call :is_port_listening %BACKEND_PORT%
if errorlevel 1 (
    echo Starting Backend on port %BACKEND_PORT%...
    start "Atlas Backend" cmd /k "cd /d "%BACKEND_DIR%" && python -m uvicorn orchestrator_v0:app --reload --host 127.0.0.1 --port %BACKEND_PORT%"
) else (
    echo Backend already running on port %BACKEND_PORT%.
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2"

call :is_port_listening %FRONTEND_PORT%
if errorlevel 1 (
    echo Starting Frontend on port %FRONTEND_PORT%...
    start "Atlas Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npx vite --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort"
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
