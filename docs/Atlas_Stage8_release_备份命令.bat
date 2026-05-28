@echo off
set "ROOT=%~dp0.."
cd /d "%ROOT%"
echo Backing up Atlas Stage 8 release version...
echo.
echo This may take a while if node_modules is included.
echo.
xcopy blackboard_day5_7 blackboard_stage8_release /E /I /H
xcopy interview-assistant-stage4-whisper interview-assistant_stage8_release /E /I /H
copy start-all.bat start-all-stage8-release.bat
echo.
echo Stage 8 release backup completed.
pause
