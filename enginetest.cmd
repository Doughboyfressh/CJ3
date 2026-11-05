@echo off
rem Pi's engine tests: the brain (Qwen3.8 Flash Next) on Pi's GPU engine. test.cmd tests the compiler and the golden
rem programs; this tests what they cannot: the kernels on real weights, the decode pass, speculation, the recorded
rem graphs at long context, and a whole brain turn. Needs the GPU to itself (nothing else running the engine), ~8 min.
rem The references are in examples\native\golden_engine\. When a change is MEANT to change the brain's output
rem (a new card, a new model), make new references deliberately, never to get a pass.
setlocal enabledelayedexpansion
cd /d "%~dp0"
set G=examples\native\golden_engine
set fail=0
for %%p in (flashk flashchat chat enginecheck) do (
  if exist out\%%p.exe del out\%%p.exe
  out\pic.exe examples\native\%%p.pi out\%%p.exe >nul
  if not exist out\%%p.exe (echo FAIL %%p did not compile & exit /b 1)
)
rem 1. the matvec kernels on real weights, against the verified outputs (gguf-py's dequantization agreed to 1.6e-7)
out\flashk.exe all w >nul
call :check kern out\flashk.txt %G%\flashk.txt 0.00001
rem 2. the decode pass: the octopus answer, 58 tokens, the same tokens and logits
out\flashchat.exe "In two sentences, what makes octopuses unusual?" 80 trace >nul
call :check trace out\flash_trace.txt %G%\octopus_trace.txt 0.001
rem 3. speculation is exact: drafted decoding gives plain greedy's tokens
out\flashchat.exe @%G%\rename_prompt.txt 200 spec > out\et_spec.txt
call :check has out\et_spec.txt "-- IDENTICAL"
rem 4. the recorded graphs (device positions, sparse attention past 2048 tokens) give live decoding's logits exactly
out\flashchat.exe @%G%\long_prompt.txt 40 trace > out\et_long_graph.txt
copy /y out\flash_trace.txt out\et_long_graph_trace.txt >nul
echo.> out\flash_nograph.flag
out\flashchat.exe @%G%\long_prompt.txt 40 trace > out\et_long_live.txt
del out\flash_nograph.flag
call :check trace out\et_long_graph_trace.txt out\flash_trace.txt 0
call :check has out\et_long_graph.txt 4721
rem 5. a whole brain turn (run_pi, compile while writing, drafts): the turn's text byte for byte. The user's chat log
rem    and the brain's memory file are kept aside and put back.
set MEM=C:\Users\Dough\laya-plus\data\knowledge\llm\ornith\brain_memory.txt
if exist out\flash_chat_log.txt copy /y out\flash_chat_log.txt out\et_chat_log_keep.txt >nul
if exist "%MEM%" copy /y "%MEM%" out\et_mem_keep.txt >nul
type nul > out\flash_chat_log.txt
out\chat.exe < %G%\brain_turn.in > out\et_brain.txt
copy /y out\flash_chat_log.txt out\et_brain_log.txt >nul
if exist out\et_chat_log_keep.txt copy /y out\et_chat_log_keep.txt out\flash_chat_log.txt >nul
if exist out\et_mem_keep.txt copy /y out\et_mem_keep.txt "%MEM%" >nul
call :check same out\et_brain_log.txt %G%\brain_turn.txt
if !fail!==0 (echo ENGINE PASS: kernels, decode, speculation, graphs at 5016 tokens, a brain turn & exit /b 0)
echo ENGINE: SOME FAILED
exit /b 1

:check
out\enginecheck.exe %* > out\et_check.txt
type out\et_check.txt
findstr /b /c:"ok" out\et_check.txt >nul
if errorlevel 1 set fail=1
exit /b 0
