@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND=%ROOT%frontend"
set "BACKEND=%ROOT%backend"

echo === Building frontend... ===
cd /d "%FRONTEND%"

call npm run build
IF %ERRORLEVEL% NEQ 0 (
    echo !!! Build failed. Exiting.
    exit /b %ERRORLEVEL%
)
echo --- Build completed successfully. ---

cd /d "%ROOT%"
echo === Copying files to backend ===

if not exist "%BACKEND%\templates" mkdir "%BACKEND%\templates"
if not exist "%BACKEND%\static" mkdir "%BACKEND%\static"

set "logfile=%TEMP%\xcopy_log_%RANDOM%.txt"

echo --- Copying index.html ---
xcopy /Y /F "%FRONTEND%\dist\index.html" "%BACKEND%\templates\" > "%logfile%"
type "%logfile%"

echo --- Copying asset files ---
xcopy /E /I /Y /F "%FRONTEND%\dist\assets" "%BACKEND%\static\assets" >> "%logfile%"
type "%logfile%"

echo --- Copy complete. Written files listed above. ===

del "%logfile%" >nul 2>&1

endlocal
