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

### Teach a spatial word or an ordering phrase

Grid rows are separated by slashes. Heed chooses a small grid on which the candidate
programs predict different answers. Give the output grid, then use the word on a new input.

```sh
out/heed grid out/lessons.txt ask mirror
# Show mirror on 1,1/2,3.
out/heed grid out/lessons.txt teach mirror 1,1/2,3 1,1/3,2
out/heed grid out/lessons.txt use "mirror, then flip" 7,8,9/4,5,6
# [[6, 5, 4], [9, 8, 7]]
out/heed order out/lessons.txt teach "biggest first" 2,1,3 3,2,1
out/heed review out/lessons.txt
```

Heed stores demonstrations by domain, phrase, and input. A new answer for the same
input corrects the earlier lesson. In `review`, conflicting practice meanings can trigger a
grid question. A taught phrase can fill a whole clause, so the same ordering demonstration
applies to both “squares sorted, biggest first” and “three smallest, biggest first.”
Standalone grid commands also know `flip` (top to bottom) and `transpose`. Ordering commands
know `reverse` and `sort`. When the initial candidates all fail, Heed runs its bounded
program search. It marks the first program that fits every saved example as provisional.

**Why four cells and three labels suffice.** The initial grid candidates are the eight
rotations and reflections (including identity) and a ninth program that appends the rows
in reverse order. A rectangle with fewer than four cells has a single row or column, so
at least one reflection agrees with identity. On a two-by-two grid with at most two
labels, a nonidentity symmetry always preserves the pattern. A minority label occurs at a
single corner, at two adjacent corners, or at two opposite corners, or the grid is uniform.
Each case admits a reflection or half-turn. On `1,1/2,3`, the unique labels 2 and 3
occupy adjacent corners. Only identity fixes both corners, so all eight symmetries produce
distinct grids. The ninth program changes the height. Thus four cells is the minimum area
for one demonstration to distinguish all nine, and three labels is the minimum at that
area. Heed finds the display by enumerating patterns up to renaming their labels. The
guarantee applies to noiseless answers from this candidate set.

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
