# Pi

A programming language that compiles itself, runs on its own from-scratch GPU engine, and carries its own
brain. No Rust, no interpreter, no CUDA toolkit, no third-party libraries — Pi is written in Pi.

## What it is

- **Self-hosting.** `examples/pic.pi` is the compiler: a Pi program that compiles Pi source to a native
  x64 executable for Windows or Linux, including itself. `seed/pic.exe` and `seed/pic` are the bootstrap
  compilers — self-reproducing fixpoints that rebuild themselves byte-for-byte, and each cross-compiles the
  other exactly. The Rust interpreter that first bootstrapped Pi has been retired.
- **Its own runtime.** `examples/native/rt.pi` provides memory, text, lists, maps, exact big integers, files
  and printing. There is no garbage collector; memory is reclaimed in regions (`mark()` / `release()`).
- **Its own GPU.** Pi emits PTX and loads it straight through `nvcuda.dll` — no CUDA toolkit. On top of that
  sits a GPU path tracer, a from-scratch autograd engine (`grad.pi`), and neural reconstruction that overfits a
  network to a single real photo, recording or scene (`nimage.pi`, `naudio.pi`, `nerf.pi`, `nimage_hr.pi`).
- **A brain.** A language model runs on Pi's own GPU engine and acts *through* Pi: it writes and runs programs
  (`run_pi`), uses a real shell and the web, and keeps a memory across conversations. The language even improves
  itself — `langgrow.pi` learns new grammar rules from the brain's own compile failures, and only reseeds the
  compiler if the full test suite still passes.

## Quick start

Windows x64:

```
build.cmd              build out\pic.exe (the compiler) from examples\pic.pi
build.cmd prog.pi      compile a program  ->  out\prog.exe
test.cmd               the suite: the self-compile fixpoint + golden-output checks
build.cmd reseed       after editing pic.pi or rt.pi: test, then promote the new compilers to the seeds
```

Linux x64 (nothing to install: the compiler and what it builds are static programs that use no libraries):

```
./build.sh             build out/pic (the compiler) from examples/pic.pi
./build.sh prog.pi     compile a program  ->  out/prog
./test.sh              the same suite, held to the same golden files
./build.sh reseed      after editing pic.pi or rt.pi: test, then promote the new compilers to the seeds
```

Either compiler builds for the other system: `pic SOURCE OUTPUT linux` or `pic SOURCE OUTPUT windows`.

## Layout

| Path | What |
|---|---|
| `examples/pic.pi` | the compiler (compiles itself) |
| `examples/native/` | the live code: runtime, GPU engine, brain, tools, path tracer, autograd, neural models |
| `seed/pic.exe`, `seed/pic` | the bootstrap compilers for Windows and Linux (self-reproducing fixpoints) |
| `build.cmd`, `test.cmd` | build and test on Windows |
| `build.sh`, `test.sh` | build and test on Linux |
| `LANGUAGE.md` | the full language — syntax, words, modules, and how it runs |
| `BRAIN.md` | the brain's design — the learning principles behind Pi's core loop |
| `NEXT.md` | the running engineering log |

The older `.pi` files directly in `examples/` predate the self-hosted compiler and don't all build yet; the
working code lives under `examples/native/`. See `LANGUAGE.md` for the details.

## What's not in this repo

The brain's resident data lives in `out/` and is intentionally git-ignored: the model's weight-derived state
snapshots, a large body of reference text, indexes, logs, and every compiled binary. A clone builds the language
and the compiler — but not the brain's local data, which stays on the machine.

## Status

A personal research project. Windows x64 and Linux x64.

On Linux the language, the runtime, files, folders, child processes (`spawn`, `par for`), sockets and the clock
all work, and the whole test suite passes against the same golden files as Windows. What is still Windows-only:
the GPU engine (it loads NVIDIA's Windows driver), `http()` (WinHTTP), and the screen, mouse, keyboard and sound
words. A program that reaches for one of those on Linux stops with a message naming it.
