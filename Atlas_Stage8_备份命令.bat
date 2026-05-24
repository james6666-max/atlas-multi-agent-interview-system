@echo off
cd /d C:\Users\hp\Desktop
echo Backing up Atlas Stage 8 working version...
echo.
echo This may take a while if node_modules is included.
echo.
xcopy blackboard_day5_7 blackboard_stage8_full-working /E /I /H
xcopy interview-assistant-stage4-whisper interview-assistant_stage8_full-working /E /I /H
copy start-all.bat start-all-stage8-working.bat
echo.
echo Backup completed.
pause
