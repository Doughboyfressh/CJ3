@echo off
rem Pi's test suite -- no Rust. Run from anywhere: test.cmd
rem 1. Self-hosting: the seed compiles the compiler (g1), g1 compiles it again (g2), g2 once more (g3); g2 and g3
rem    must be byte-identical. g2 is the compiler under test. If g2 differs from the seed, the seed is stale
rem    (pic.pi changed): `build.cmd reseed` makes g2 the new seed once this suite passes.
rem 2. Every program in examples\native\golden\ is compiled by g2 and run, fed golden\<name>.in as its input if
rem    there is one (else no input); its output must match the golden file byte for byte.
rem 3. The agent's memory: two runs sharing a memory file.
rem The Linux compiler (seed\pic) is built from the same source: g2 cross-compiles it and says whether the one in
rem seed\ is current. test.sh is this suite on Linux, held to the same golden files.
rem Set PI_NO_GPU=1 on a machine without an NVIDIA GPU (CI does) to skip the one GPU golden program.
setlocal enabledelayedexpansion
cd /d "%~dp0"
if not exist out mkdir out
set fail=0
set n=0
seed\pic.exe examples\pic.pi out\t_g1.exe >nul
if not exist out\t_g1.exe (echo FAIL: the seed did not compile the compiler & exit /b 1)
out\t_g1.exe examples\pic.pi out\t_g2.exe >nul
out\t_g2.exe examples\pic.pi out\t_g3.exe >nul
fc /b out\t_g2.exe out\t_g3.exe >nul
if errorlevel 1 (echo FAIL fixpoint: the compiler does not reproduce itself & set fail=1) else (echo ok   fixpoint: the compiler reproduces itself)
fc /b out\t_g2.exe seed\pic.exe >nul
if errorlevel 1 (echo note seed is stale: run build.cmd reseed once this passes) else (echo ok   seed is current)
out\t_g2.exe examples\pic.pi out\t_gl linux >nul
fc /b out\t_gl seed\pic >nul
if errorlevel 1 (echo note the Linux seed is stale: run build.cmd reseed once this passes) else (echo ok   the Linux compiler built here is seed\pic)
for %%f in (examples\native\golden\*.out) do (
  set p=%%~nf
  set skip=0
  if defined PI_NO_GPU if /i "!p!"=="gpuforms" set skip=1
  if !skip!==1 (
    echo skip !p!: needs an NVIDIA GPU
  ) else (
  set /a n+=1
  if exist out\t_!p!.exe del out\t_!p!.exe
  out\t_g2.exe examples\native\!p!.pi out\t_!p!.exe >nul
  if not exist out\t_!p!.exe (
    echo FAIL !p!: did not compile
    set fail=1
  ) else (
    if exist examples\native\golden\!p!.in (
      out\t_!p!.exe < examples\native\golden\!p!.in > out\t_!p!.txt
    ) else (
      out\t_!p!.exe < nul > out\t_!p!.txt
    )
    fc /b out\t_!p!.txt %%f >nul
    if errorlevel 1 (echo FAIL !p!: output differs from golden & set fail=1) else (echo ok   !p!)
  )
  )
)
rem 3. The agent remembers across runs: teach it with a memory file, start it afresh, ask; the answers must match.
if exist out\t_agent.exe (
  if exist out\t_mem.txt del out\t_mem.txt
  out\t_agent.exe out\t_mem.txt < examples\native\golden\agent_teach.in > nul
  out\t_agent.exe out\t_mem.txt < examples\native\golden\agent_recall.in > out\t_recall.txt
  fc /b out\t_recall.txt examples\native\golden\agent_recall.expect >nul
  if errorlevel 1 (echo FAIL agent memory: it did not remember across runs & set fail=1) else (echo ok   agent remembers across runs)
)
rem Verify teaching, correction and transfer in separate processes.
if exist out\t_heed.exe (
  if exist out\t_heed.lessons del out\t_heed.lessons
  (
    out\t_heed.exe memory out\t_heed.lessons teach "sum of ravels" 2,3 10
    out\t_heed.exe memory out\t_heed.lessons teach "product of ravels" 2,3 24
    out\t_heed.exe memory out\t_heed.lessons use "product of ravels" 3,5,7
    out\t_heed.exe memory out\t_heed.lessons use "count ravels" 3,5,7
    out\t_heed.exe memory out\t_heed.lessons teach "product of ravels" 2,3 12
    out\t_heed.exe memory out\t_heed.lessons use "product of ravels" 3,5,7
    out\t_heed.exe memory out\t_heed.lessons teach "sum of twill" 2,3 13
    out\t_heed.exe memory out\t_heed.lessons teach "sum of twill" 3,4 25
    out\t_heed.exe memory out\t_heed.lessons use "product of twill" 2,3,4
    out\t_heed.exe memory out\t_heed.lessons teach "sum of cubes" 2 8
    out\t_heed.exe memory out\t_heed.lessons teach "sum of cubes" 3 27
    out\t_heed.exe memory out\t_heed.lessons teach "sum of cubes" 4 64
    out\t_heed.exe memory out\t_heed.lessons teach "sum of cubes" 2,3 35
    out\t_heed.exe memory out\t_heed.lessons use "sum of cubes" 4,5
    out\t_heed.exe grid out\t_heed.lessons ask mirror
    out\t_heed.exe grid out\t_heed.lessons teach mirror 1,1/2,3 1,1/3,2
    out\t_heed.exe grid out\t_heed.lessons use "mirror, then flip" 7,8,9/4,5,6
    out\t_heed.exe order out\t_heed.lessons ask "biggest first"
    out\t_heed.exe order out\t_heed.lessons teach "biggest first" 2,1,3 3,2,1
    out\t_heed.exe order out\t_heed.lessons use "reverse, biggest first" 5,1,2,4
    out\t_heed.exe order out\t_heed.lessons teach mirror 2,1,3 3,1,2
    out\t_heed.exe grid out\t_heed.lessons use mirror 9,2/7,4
    out\t_heed.exe grid out\t_heed.lessons teach mirror 1,1/2,3 2,3/1,1
    out\t_heed.exe order out\t_heed.lessons use mirror 7,2,9
    out\t_heed.exe grid out\t_heed.lessons use mirror 8,2/7,9
    out\t_heed.exe grid out\t_heed.lessons teach tess 1,2/3,4 1,2,1,2/3,4,3,4
    out\t_heed.exe grid out\t_heed.lessons use tess 7,8/4,5/9,1
    out\t_heed.exe grid out\t_heed.lessons teach zuri 1,2/3,4 2,1/4,3
    out\t_heed.exe grid out\t_heed.lessons teach zuri 8,7/6,5 6,5/8,7
    out\t_heed.exe grid out\t_heed.lessons use zuri 1,4/8,7/5,6
    out\t_heed.exe grid out\t_heed.lessons teach zuri 8,2/3,4 3,4/8,2
    out\t_heed.exe grid out\t_heed.lessons teach zuri 0,2/3,4 3,4/0,2
    out\t_heed.exe grid out\t_heed.lessons use zuri 1,4/8,7/5,6
    out\t_heed.exe grid out\t_heed.lessons use "zuri, then transpose" 2,7/9,4/6,8
    out\t_heed.exe memory out\t_heed.lessons use "sum of cubes" 4,5
  ) > out\t_heed_memory.txt
  fc /b out\t_heed_memory.txt examples\native\golden\heed_memory.expect >nul
  if errorlevel 1 (echo FAIL Heed lesson memory & set fail=1) else (echo ok   Heed transfers corrections across runs)
)
if !fail!==0 (echo ALL PASS: fixpoint and !n! programs & exit /b 0)
echo SOME FAILED
exit /b 1
