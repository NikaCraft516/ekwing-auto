@echo off
setlocal
rem Run ekwing_auto.py with whatever Python is available.
rem Usage: ekw.bat --url "https://www.ekwing.com/hw/do?hid=<ID>" --dry-run

set "PYEXE="

rem 1) py launcher
where py >nul 2>nul
if not errorlevel 1 set "PYEXE=py -3"

rem 2) python on PATH
if not defined PYEXE (
  where python >nul 2>nul
  if not errorlevel 1 set "PYEXE=python"
)

rem 3) common install locations
if not defined PYEXE (
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
)
if not defined PYEXE (
  if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PYEXE=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
)

if not defined PYEXE (
  echo [x] Python 3.9+ not found. Install it or edit PYEXE in this file.
  pause
  exit /b 1
)

set "CDP_PORT=9224"
set "PYTHONIOENCODING=utf-8"
%PYEXE% "%~dp0ekwing_auto.py" %*

if errorlevel 1 (
  echo.
  echo [!] exit code %errorlevel%
  pause
)
endlocal
