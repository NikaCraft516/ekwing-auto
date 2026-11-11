@echo off
setlocal
rem ============================================================
rem  Launch a scriptable Chromium browser (Edge preferred, fallback Chrome)
rem    start-browser.bat              auto
rem    start-browser.bat edge         force Edge
rem    start-browser.bat chrome 9226  force Chrome on port 9226
rem ============================================================

set "WHICH=%~1"
if "%WHICH%"=="" set "WHICH=auto"
set "PORT=%~2"
if "%PORT%"=="" set "PORT=9224"

set "EDGE1=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
set "EDGE2=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
set "EDGE3=%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"
set "CHROME1=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHROME2=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set "CHROME3=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

set "EXE="
set "NAME="

if /i "%WHICH%"=="chrome" goto :trychrome
if /i "%WHICH%"=="edge" goto :tryedge

:tryedge
if exist "%EDGE1%" set "EXE=%EDGE1%" & set "NAME=Edge" & goto :launch
if exist "%EDGE2%" set "EXE=%EDGE2%" & set "NAME=Edge" & goto :launch
if exist "%EDGE3%" set "EXE=%EDGE3%" & set "NAME=Edge" & goto :launch
if /i "%WHICH%"=="edge" goto :notfound

:trychrome
if exist "%CHROME1%" set "EXE=%CHROME1%" & set "NAME=Chrome" & goto :launch
if exist "%CHROME2%" set "EXE=%CHROME2%" & set "NAME=Chrome" & goto :launch
if exist "%CHROME3%" set "EXE=%CHROME3%" & set "NAME=Chrome" & goto :launch
goto :notfound

:launch
set "PROFILE=%LOCALAPPDATA%\ekwing-auto-profile\%NAME%"
if not exist "%PROFILE%" mkdir "%PROFILE%"

echo [i] browser : %NAME%
echo [i] exe     : %EXE%
echo [i] profile : %PROFILE%
echo [i] port    : %PORT%
echo.
echo     Log in to ekwing.com in the window that opens.
echo     Keep that window open - the tool drives it via the debug port.
echo.

start "" "%EXE%" --remote-debugging-port=%PORT% --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check --window-size=1400,1000 "https://www.ekwing.com/site/index"
exit /b 0

:notfound
echo [x] No Edge or Chrome found. Edit the EDGE1 / CHROME1 paths in this file.
pause
exit /b 1
