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
- **Its own machine.** Softwell is the only GPU, CPU, SSD, and RAM Pi needs: 64 KB of RAM, a 1 MB SSD, and the chip. No CUDA toolkit, no driver, and no physical module.
- **A brain.** A language model runs on Pi's own GPU engine and acts *through* Pi: it writes and runs programs
  (`run_pi`), uses a real shell and the web, and keeps a memory across conversations. The language even improves
  itself — `langgrow.pi` learns new grammar rules from the brain's own compile failures, and only reseeds the
  compiler if the full test suite still passes.

- **Language, its own way.** `tonguelib.pi` learns a language from example sentences with no network and
  nothing trained: it keeps the smallest set of readable rules that explains everything it heard, and checks
  each rule against all of it. `tongue.pi` measures it on the SCAN benchmark: from the 422 shortest commands
  it reads the other 20,488 correctly, including every sentence the benchmark's splits hold back. `heed.pi`
  uses the same learner on the mind's own tasks: an English instruction Pi was never given is read as a
  program and run.

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

## Teach Heed a word

Heed can learn where a word acts in a list instruction. For example, doubling each number and
doubling the final sum both explain why 2 and 3 give 10. A product distinguishes those readings.
Run these from the repository root on Linux. Each command starts a fresh process.

```sh
./build.sh examples/native/heed.pi
out/heed memory out/lessons.txt teach "sum of ravels" 2,3 10
# What is product of ravels on 2,3?
out/heed memory out/lessons.txt teach "product of ravels" 2,3 24
# Learned ravels: (e * 2) before reduction.
out/heed memory out/lessons.txt use "product of ravels" 3,5,7
# 840
```

On Windows, build with `build.cmd examples\native\heed.pi` and run `out\heed.exe`.
The lesson file stores observations. Repeating the same word, operation, and input with a new
answer corrects that observation. The learner tries small shifts and scales first. If all of
them fail, it tries a bounded search for a scalar expression and checks it against every saved
example for the word. Supported operations are sum, product, count, largest, and smallest on
nonempty lists of integers.

Run `out/heed review out/lessons.txt` to use that memory in the ordinary Heed curriculum.
When practice examples support multiple readings, Heed can save them and ask for a distinguishing
example. Answer with `teach` and rerun `review` to see how the correction transfers.

## Layout

| Path | What |
|---|---|
| `examples/pic.pi` | the compiler (compiles itself) |
| `examples/native/` | the live code: runtime, GPU engine, brain, tools, path tracer, autograd, neural models |
| `softwell/` | the software machine: one clock, CPU, 64 KB RAM, SSD, and the GPU. No physical chip |
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
all work, and the whole test suite passes against the same golden files as Windows. Softwell is the machine on
both hosts. There is no NVIDIA driver to load. What is still Windows-only: `http()` (WinHTTP), and the screen,
mouse, keyboard and sound words. A program that reaches for one of those on Linux stops with a message naming it.
