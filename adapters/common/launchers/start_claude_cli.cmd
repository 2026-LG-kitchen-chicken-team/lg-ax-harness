@echo off
setlocal
chcp 65001 >nul
title LG AX - Claude Code CLI
cd /d "%~dp0"
call :uv || goto fail
set "PY=uv run --no-project --python 3.12 python"
%PY% judge.py prepare --engine claude --ui cli || goto fail
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
cd /d "%~dp0claude"
echo Claude Code를 시작합니다 (Opus 5.5, 추론 중간). 끝내려면 /exit
claude --model claude-opus-5-5 --effort medium
if errorlevel 1 pause
exit /b

:uv
where uv >nul 2>nul && exit /b 0
if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul && exit /b 0
echo uv가 없습니다. 공식 안내: https://docs.astral.sh/uv/getting-started/installation/
echo 공식 설치 명령: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
set "ANSWER="
set /p "ANSWER=지금 이 공식 설치 명령을 실행할까요? [y/N] "
if /i not "%ANSWER%"=="y" exit /b 1
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
exit /b

:fail
echo.
echo 시작하지 못했습니다. 위 메시지를 확인하세요. 같은 내용의 수동 절차는 README.md에 있습니다.
pause
exit /b 1
