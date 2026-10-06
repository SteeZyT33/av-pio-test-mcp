@echo off
REM Explicit stdio only. No pip, venv, installation, HTTP or transport fallback.
REM Usage: vwx-mcp.bat C:\trusted\python.exe C:\private\config.json
if "%~1"=="" exit /b 2
if "%~2"=="" exit /b 2
"%~1" -I "%~dp0..\mcp-server\vwx_mcp_server.py" --config "%~2"
exit /b %errorlevel%
