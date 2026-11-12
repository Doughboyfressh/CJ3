#!/bin/sh
# Build Pi on Linux -- what build.cmd does on Windows. seed/pic is Pi's own compiler (written in Pi, compiled by
# itself). It compiles examples/pic.pi twice so the compiler in use always has the current source's code
# generation, then compiles whatever you name.
#   ./build.sh                    build out/pic from examples/pic.pi
#   ./build.sh prog.pi            compile prog.pi -> out/<prog>
#   ./build.sh prog.pi out/name   compile prog.pi -> out/name
#   ./build.sh prog.pi x.exe windows    the same program for Windows (pic cross-compiles either way)
#   ./build.sh reseed             after editing pic.pi or rt.pi: run test.sh and, if it passes, make the new
#                                 compilers the seeds (seed/pic for Linux and seed/pic.exe for Windows)
cd "$(dirname "$0")" || exit 1
mkdir -p out
if [ "$1" = "reseed" ]; then
  ./test.sh || { echo "reseed: the suite failed, the seeds are unchanged"; exit 1; }
  cp out/t_g2 seed/pic && chmod +x seed/pic && cp out/t_gw.exe seed/pic.exe
  echo "reseed: seed/pic and seed/pic.exe are now the compilers built from the current examples/pic.pi"
  exit 0
fi
rm -f out/pic1 out/pic
seed/pic examples/pic.pi out/pic1 > /dev/null
[ -x out/pic1 ] || { echo "build: the seed failed to compile the compiler"; exit 1; }
out/pic1 examples/pic.pi out/pic > /dev/null
[ -x out/pic ] || { echo "build: the compiler failed to compile itself"; exit 1; }
if [ -z "$1" ]; then echo "Built out/pic"; exit 0; fi
OUT="$2"
[ -n "$OUT" ] || OUT="out/$(basename "$1" .pi)"
rm -f "$OUT"
if [ -n "$3" ]; then out/pic "$1" "$OUT" "$3" > /dev/null; else out/pic "$1" "$OUT" > /dev/null; fi
if [ -f "$OUT" ]; then echo "Built $OUT"; exit 0; fi
echo "build: $1 did not compile"
exit 1
