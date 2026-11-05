@echo off
rem Build Pi -- no Rust anywhere. seed\pic.exe is Pi's own compiler (written in Pi, compiled by itself).
rem It compiles examples\pic.pi twice so the compiler in use always has the current source's code generation
rem (one pass from an older seed gives the new logic but the old code), then compiles whatever you name.
rem Usage:
rem   build.cmd                     build out\pic.exe from examples\pic.pi
rem   build.cmd prog.pi             compile prog.pi -> out\<prog>.exe
rem   build.cmd prog.pi out.exe     compile prog.pi -> out.exe
rem   build.cmd reseed              after editing pic.pi: run test.cmd and, if it passes, make the new compiler the seed
setlocal
cd /d "%~dp0"
if not exist out mkdir out
if /i "%~1"=="reseed" goto reseed
rem never let a compiler left from an earlier build pass for this one
if exist out\pic1.exe del out\pic1.exe
if exist out\pic.exe del out\pic.exe
seed\pic.exe examples\pic.pi out\pic1.exe >nul
if not exist out\pic1.exe (echo build: the seed failed to compile the compiler & exit /b 1)
out\pic1.exe examples\pic.pi out\pic.exe >nul
if not exist out\pic.exe (echo build: the compiler failed to compile itself & exit /b 1)
if "%~1"=="" ( echo Built out\pic.exe & exit /b 0 )
set "OUT=%~2"
if "%OUT%"=="" set "OUT=out\%~n1.exe"
out\pic.exe "%~1" "%OUT%" >nul
if exist "%OUT%" (echo Built %OUT% & exit /b 0)
echo build: %~1 did not compile
exit /b 1

:reseed
call "%~dp0test.cmd"
if errorlevel 1 (echo reseed: the suite failed, the seed is unchanged & exit /b 1)
copy /y out\t_g2.exe seed\pic.exe >nul
echo reseed: seed\pic.exe is now the compiler built from the current examples\pic.pi
exit /b 0
