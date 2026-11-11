@echo off
chcp 65001 >nul
rem 兼容旧入口：等价于 start-browser.bat chrome
call "%~dp0start-browser.bat" chrome %*
