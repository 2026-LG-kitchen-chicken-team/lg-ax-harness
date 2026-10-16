@echo off
setlocal
chcp 65001 >nul
title LG AX - Codex app
cd /d "%~dp0"
call :uv || goto fail
set "PY=uv run --no-project --python 3.12 python"
%PY% judge.py prepare --engine codex --ui gui || goto fail
start "LG AX - Codex observer" /min cmd /c "%PY% judge.py observe --engine codex --keep-following --open || pause"
echo 실행 관찰 창을 작은 창으로 켰습니다. 첫 질문을 보내면 실행 대시보드가 브라우저에 열립니다.
codex app "%~dp0codex" || goto fail
echo.
echo Codex 앱에서 codex 폴더가 열렸는지 확인하고 질문하세요. 실행 관찰은 작은 창에서 계속됩니다.
pause
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
