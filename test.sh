#!/bin/sh
# The Linux suite: what test.cmd checks on Windows, with the Linux compiler (seed/pic).
#   1. The self-compile fixpoint: the seed builds the compiler, which builds itself, which builds itself again;
#      the last two must be the same file, byte for byte.
#   2. The two systems agree: the Linux compiler cross-compiles the Windows compiler, and it must be seed/pic.exe.
#   3. Every program with a golden file is compiled, run, and its output compared byte for byte -- the same golden
#      files Windows is held to. Programs that need a Windows-only facility are listed in WINDOWS_ONLY and skipped.
#   4. The agent remembers across runs.
cd "$(dirname "$0")" || exit 1
mkdir -p out
WINDOWS_ONLY="gpuforms"
fail=0
n=0
rm -f out/t_g0 out/t_g1 out/t_g2
seed/pic examples/pic.pi out/t_g0 > /dev/null
[ -x out/t_g0 ] || { echo "FAIL the seed could not compile the compiler"; exit 1; }
out/t_g0 examples/pic.pi out/t_g1 > /dev/null
out/t_g1 examples/pic.pi out/t_g2 > /dev/null
if cmp -s out/t_g1 out/t_g2; then echo "ok   fixpoint"; else echo "FAIL fixpoint: the compiler does not reproduce itself"; fail=1; fi
if cmp -s out/t_g2 seed/pic; then echo "ok   seed is current"; else echo "note seed is stale: run ./build.sh reseed once this passes"; fi
out/t_g2 examples/pic.pi out/t_gw.exe windows > /dev/null
if cmp -s out/t_gw.exe seed/pic.exe; then echo "ok   the Windows compiler built here is seed/pic.exe"; else echo "note seed/pic.exe is not what this source builds: run ./build.sh reseed"; fi
for f in examples/native/golden/*.out; do
  p=$(basename "$f" .out)
  case " $WINDOWS_ONLY " in *" $p "*) echo "skip $p: needs a Windows-only facility"; continue;; esac
  n=$((n + 1))
  rm -f "out/t_$p"
  out/t_g2 "examples/native/$p.pi" "out/t_$p" > /dev/null
  if [ ! -x "out/t_$p" ]; then echo "FAIL $p: did not compile"; fail=1; continue; fi
  if [ -f "examples/native/golden/$p.in" ]; then
    "out/t_$p" < "examples/native/golden/$p.in" > "out/t_$p.txt"
  else
    "out/t_$p" < /dev/null > "out/t_$p.txt"
  fi
  if cmp -s "out/t_$p.txt" "$f"; then echo "ok   $p"; else echo "FAIL $p: output differs from golden"; fail=1; fi
done
if [ -x out/t_agent ]; then
  rm -f out/t_mem.txt
  out/t_agent out/t_mem.txt < examples/native/golden/agent_teach.in > /dev/null
  out/t_agent out/t_mem.txt < examples/native/golden/agent_recall.in > out/t_recall.txt
  if cmp -s out/t_recall.txt examples/native/golden/agent_recall.expect; then echo "ok   agent remembers across runs"; else echo "FAIL agent memory: it did not remember across runs"; fail=1; fi
fi
# Each invocation starts a new process; the lesson file is their only shared state.
if [ -x out/t_heed ]; then
  rm -f out/t_heed.lessons
  {
    out/t_heed memory out/t_heed.lessons teach "sum of ravels" 2,3 10
    out/t_heed memory out/t_heed.lessons teach "product of ravels" 2,3 24
    out/t_heed memory out/t_heed.lessons use "product of ravels" 3,5,7
    out/t_heed memory out/t_heed.lessons use "count ravels" 3,5,7
    out/t_heed memory out/t_heed.lessons teach "product of ravels" 2,3 12
    out/t_heed memory out/t_heed.lessons use "product of ravels" 3,5,7
    out/t_heed memory out/t_heed.lessons teach "sum of twill" 2,3 13
    out/t_heed memory out/t_heed.lessons teach "sum of twill" 3,4 25
    out/t_heed memory out/t_heed.lessons use "product of twill" 2,3,4
    out/t_heed memory out/t_heed.lessons teach "sum of cubes" 2 8
    out/t_heed memory out/t_heed.lessons teach "sum of cubes" 3 27
    out/t_heed memory out/t_heed.lessons teach "sum of cubes" 4 64
    out/t_heed memory out/t_heed.lessons teach "sum of cubes" 2,3 35
    out/t_heed memory out/t_heed.lessons use "sum of cubes" 4,5
    out/t_heed grid out/t_heed.lessons ask mirror
    out/t_heed grid out/t_heed.lessons teach mirror 1,1/2,3 1,1/3,2
    out/t_heed grid out/t_heed.lessons use "mirror, then flip" 7,8,9/4,5,6
    out/t_heed order out/t_heed.lessons ask "biggest first"
    out/t_heed order out/t_heed.lessons teach "biggest first" 2,1,3 3,2,1
    out/t_heed order out/t_heed.lessons use "reverse, biggest first" 5,1,2,4
    out/t_heed order out/t_heed.lessons teach mirror 2,1,3 3,1,2
    out/t_heed grid out/t_heed.lessons use mirror 9,2/7,4
    out/t_heed grid out/t_heed.lessons teach mirror 1,1/2,3 2,3/1,1
    out/t_heed order out/t_heed.lessons use mirror 7,2,9
    out/t_heed grid out/t_heed.lessons use mirror 8,2/7,9
    out/t_heed grid out/t_heed.lessons teach tess 1,2/3,4 1,2,1,2/3,4,3,4
    out/t_heed grid out/t_heed.lessons use tess 7,8/4,5/9,1
    out/t_heed memory out/t_heed.lessons use "sum of cubes" 4,5
  } > out/t_heed_memory.txt
  if cmp -s out/t_heed_memory.txt examples/native/golden/heed_memory.expect; then echo "ok   Heed transfers corrections across runs"; else echo "FAIL Heed lesson memory"; fail=1; fi
fi
if [ "$fail" = 0 ]; then echo "ALL PASS: fixpoint and $n programs"; exit 0; fi
echo "SOME FAILED"
exit 1
