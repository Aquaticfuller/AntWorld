@echo off
setlocal
pushd "%~dp0.." || exit /b 1
if exist "%LOCALAPPDATA%\Python\bin\python.exe" goto local_python
where py.exe >nul 2>&1
if not errorlevel 1 goto launcher
python -B -X utf8 -m op0 --micro serve %*
goto finished

:local_python
"%LOCALAPPDATA%\Python\bin\python.exe" -B -X utf8 -m op0 --micro serve %*
goto finished

:launcher
py -3 -B -X utf8 -m op0 --micro serve %*

:finished
set "result=%errorlevel%"
popd
exit /b %result%
