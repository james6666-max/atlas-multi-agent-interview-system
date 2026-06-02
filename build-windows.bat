@echo off
setlocal
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%blackboard_day5_7"
set "FRONTEND_DIR=%ROOT%interview-assistant-stage4-whisper"
set "CONDA_ENV=chuangxin"

echo =========================================
echo  Atlas - Windows packaging
echo =========================================
echo  Backend conda env: %CONDA_ENV%
echo.

echo [1/4] Installing backend deps + PyInstaller...
call conda run -n %CONDA_ENV% pip install -r "%BACKEND_DIR%\requirements.txt" pyinstaller
if errorlevel 1 goto :fail

echo.
echo [2/4] Freezing backend (PyInstaller onedir)...
pushd "%BACKEND_DIR%"
call conda run -n %CONDA_ENV% pyinstaller atlas_backend.spec --noconfirm
popd
if not exist "%BACKEND_DIR%\dist\atlas-backend\atlas-backend.exe" (
    echo.
    echo ERROR: backend exe not produced ^(blackboard_day5_7\dist\atlas-backend\atlas-backend.exe^).
    echo Check the PyInstaller output above; you may need to add missing modules to
    echo atlas_backend.spec hiddenimports, then re-run.
    goto :fail
)
echo Backend frozen OK.

echo.
echo [3/4] Installing frontend deps...
pushd "%FRONTEND_DIR%"
call npm install
if errorlevel 1 ( popd & goto :fail )

echo.
echo [4/4] Building Windows installer (electron-builder NSIS)...
call npm run package-win
popd
if errorlevel 1 goto :fail

echo.
echo =========================================
echo  DONE. Installer:
echo  %FRONTEND_DIR%\release\
echo =========================================
goto :done

:fail
echo.
echo =========================================
echo  BUILD FAILED - see messages above.
echo =========================================

:done
endlocal
pause
