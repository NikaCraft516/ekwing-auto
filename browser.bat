@echo off
setlocal
rem ============================================================
rem  Launch a scriptable Chromium browser (Edge preferred, fallback Chrome)
rem    browser.bat              auto
rem    browser.bat edge         force Edge
rem    browser.bat chrome 9226  force Chrome on port 9226
rem
rem  NOTE: one --user-data-dir can only have one browser instance. If an
rem  instance is already running, a new chrome.exe just hands its tab to
rem  the old process and --remote-debugging-port is IGNORED - the port
rem  never opens. So: reuse a live port, otherwise stop the stale
rem  instance that was started without the debug flag.
rem
rem  Keep this file ASCII-only: cmd.exe parses .bat with the OEM codepage,
rem  and UTF-8 Chinese in comments breaks quoting/parsing.
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
set "EXENAME="

if /i "%WHICH%"=="chrome" goto :trychrome
if /i "%WHICH%"=="edge" goto :tryedge

:tryedge
if exist "%EDGE1%" set "EXE=%EDGE1%" & set "NAME=Edge" & set "EXENAME=msedge.exe" & goto :launch
if exist "%EDGE2%" set "EXE=%EDGE2%" & set "NAME=Edge" & set "EXENAME=msedge.exe" & goto :launch
if exist "%EDGE3%" set "EXE=%EDGE3%" & set "NAME=Edge" & set "EXENAME=msedge.exe" & goto :launch
if /i "%WHICH%"=="edge" goto :notfound

:trychrome
if exist "%CHROME1%" set "EXE=%CHROME1%" & set "NAME=Chrome" & set "EXENAME=chrome.exe" & goto :launch
if exist "%CHROME2%" set "EXE=%CHROME2%" & set "NAME=Chrome" & set "EXENAME=chrome.exe" & goto :launch
if exist "%CHROME3%" set "EXE=%CHROME3%" & set "NAME=Chrome" & set "EXENAME=chrome.exe" & goto :launch
goto :notfound

:launch
set "PROFILE=%LOCALAPPDATA%\ekwing-auto-profile\%NAME%"
if not exist "%PROFILE%" mkdir "%PROFILE%"

echo [i] browser : %NAME%
echo [i] exe     : %EXE%
echo [i] profile : %PROFILE%
echo [i] port    : %PORT%
echo.

rem --- 1) port already listening: an instance with the debug port is up, reuse it
powershell -NoProfile -Command "try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',%PORT%);$c.Close();exit 0}catch{exit 1}"
if not errorlevel 1 (
  echo [i] port %PORT% is already listening - reusing the running browser.
  echo     bringing its window to the front ^(it may be minimized^).
  call :show
  echo     close that window first if you want a fresh login.
  exit /b 0
)

rem --- 2) profile is in use but the port is closed: stale instance without the
rem         debug flag. Stop it, otherwise the new launch cannot open the port.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq '%EXENAME%' -and $_.CommandLine -like '*ekwing-auto-profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
powershell -NoProfile -Command "Start-Sleep -Milliseconds 400"

echo     Log in to ekwing.com in the window that opens.
echo     Keep that window open - the tool drives it via the debug port.
echo     ^(login is remembered in the separate profile above^)
echo.

start "" "%EXE%" --remote-debugging-port=%PORT% --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check --window-size=1400,1000 "https://www.ekwing.com/site/index"

rem --- 3) wait until the debug port really answers (about 12s max)
powershell -NoProfile -Command "for($i=0;$i -lt 40;$i++){try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',%PORT%);$c.Close();exit 0}catch{Start-Sleep -Milliseconds 300}};exit 1"
if errorlevel 1 (
  echo.
  echo [x] browser started, but debug port %PORT% did not open.
  echo     Usually a security suite blocking it, or the port is taken. Try:
  echo       browser.bat %WHICH% 9225
  echo     then: ekw.bat --url "..." --port 9225
  pause
  exit /b 1
)

rem --- 4) make sure the window is actually visible (not minimized / behind)
call :show
echo [i] debug port %PORT% is ready - now run ekw.bat.
exit /b 0

rem ------------------------------------------------------------------
rem  :show - restore and foreground this profile's browser window.
rem  Chrome may start minimized when launched from a script, and a reused
rem  instance may be sitting minimized - either way the user sees nothing.
rem  P/Invoke lives in show-browser.ps1 to avoid nested-quote hell in .bat.
rem ------------------------------------------------------------------
:show
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0show-browser.ps1" %EXENAME%
exit /b 0

:notfound
echo [x] No Edge or Chrome found. Edit the EDGE1 / CHROME1 paths in this file.
pause
exit /b 1
