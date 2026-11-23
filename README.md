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
- **Its own machine.** Softwell is the only GPU, CPU, SSD, and RAM Pi needs: 64 KB of RAM, an 8 MB SSD, and the chip. No CUDA toolkit, no driver, and no physical module.
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

## Learn a door rule by acting

Build Heed, then run three episodes from the repository root:

```sh
out/heed room hall follow out/doors.obs
out/heed room annex follow out/doors.obs
out/heed room annex follow
```

Use a new observation file for the first episode. The room layout, available
moves and switch state are public. The simulator's `follow` or `latch` setting
controls the first door and is private to the simulator. Softwell checks each
attempt; Mind evaluates two candidate door rules. With both candidates viable,
Heed searches for a reachable action where they predict different outcomes.
It then plans a path to the exit. The observation file stores only switch state,
whether it has ever been on in that episode, and whether a crossing succeeded.
Reuse it across layouts with the same mechanism. Omitting the file starts cold.

### Discover a memory from action histories

`out/heed explore hall latch out/events.obs` searches 19 candidate rules:
the current switch state, or a threshold of one to three on elapsed actions
or one of five observable event counts. Heed plans a reachable experiment
that minimizes the largest group of rules left after a door crossing. It
starts each experiment from the room entrance and records the action history
and observed outcome. Restart with `out/heed explore annex latch out/events.obs`
to transfer that evidence. Use a separate file for each fixed mechanism.
Supported mechanisms are `follow`, `latch`, `retry`, `delay`, and `sequence`.
When count rules contradict recorded crossings or cannot lead to a goal or
experiment, Pi also constructs Mind folds over ordered pairs of event types.
The three templates distinguish a strict first-occurrence order, an ordered
subsequence, and the first event of a pair. Each program is checked against
the raw recorded crossings. Planning uses transition tables evaluated from
the surviving programs. New event files retain every distinct trial history
and its crossing outcome; older files can be replayed as partial evidence.

For an automated transfer comparison run `python tools/door_transfer.py out/heed`
after building Heed. Each mechanism is learned in the hall, then exercised in
46 other layouts with and without the event file. Each run starts a fresh
process. Actions include experiments and the final goal route; resetting a
trial is free. The experiment-selection policy gives identification priority
when several rules remain. The timer excludes compilation.

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
answer corrects that observation. The same file is a Mind lesson: a word with one meaning becomes a building block the search can use, and Softwell runs a program made from it. The learner tries small shifts and scales first. If all of
them fail, it tries a bounded search for a scalar expression and checks it against every saved
example for the word. Supported operations are sum, product, count, largest, and smallest on
nonempty lists of integers.

When the scalar search runs out of explanations, `heed memory` can learn a rule for
the endpoints of a list, scoped to the taught phrase. Two independent examples anchor a
linear readout of the first and last numbers. A missed answer can recruit a rectifier
of their difference. Pi searches integer thresholds between the smallest and largest
of zero and the observed differences. It solves isolated roots directly and checks up
to 256 additional thresholds across unresolved intervals. If any interval exceeds the
remaining budget, Pi asks for more evidence. When verified models disagree it seeks
a separate example whose answer settles the requested prediction. The
update preserves both anchor answers exactly. Pi keeps integer-weight programs that
reproduce every lesson for the phrase and asks for the answer when their predictions
disagree. Correcting a lesson refits the network. For a runnable example, build
`examples/native/witnesscheck.pi`.

When two examples for the same phrase have the same endpoints and different
answers, Heed also searches positional features. Softwell's software GPU runs
an equality check at each list position. Pi uses the results to filter fixed
offsets from either end and a length-dependent middle (right middle for even
lengths). Mind replays each surviving expression against every lesson. A query
on which those expressions disagree prompts another lesson. During teaching,
Softwell evaluates which positions the surviving selectors would read at each
length. Pi asks for the shortest list on which all selectors are defined and
every answer identifies a single selector, using distinct integers as labels.

Mind can load the same Heed lesson file to reuse a resolved positional selector.
When exactly one selector survives for a phrase, the lesson reader gives it the
full phrase name and a list-to-integer type. For a worked transfer example,
`witnesscheck` stores and reloads the vocabulary on Softwell's software SSD and
searches for a new operation that calls the learned selector.

When simpler rules fail, Heed can combine two positional skills learned from
other phrases with the same reducer. Softwell evaluates four conditions on
each lesson: first below last, last below first, equal endpoints, and even
length. A switch must use different skills and have evidence on both sides.
If switches disagree, Heed searches short ascending, descending, and tied-end
examples for a question that minimizes the largest group remaining after an
answer. A unique decision is exported as a typed Mind operation.

If those gates fail, Pi tries comparisons of a previously learned position
with each integer threshold from -4 to 4. It also compares two selectors
in either order, including a learned position against an endpoint. For these
comparisons the second input supplies the threshold on every example. The two outcomes may use a learned
position or an endpoint. Softwell evaluates the threshold comparisons, and
Mind verifies each resulting conditional against every lesson. Question
selection also tries changing one observation at a time at a candidate
threshold, keeping the rest of the input fixed.

During ordinary teaching Heed can discover a named source automatically when
the target differs from a previous list-to-integer skill by a constant. With
two distinct target answers it compares earlier skills on every saved target
observation. If sources compete, it tries single-position changes to a lesson
and asks a question that splits their predictions. With at least three distinct
inputs and one matching nonzero offset, it records the named dependency and
replays it on later corrections. Direct copies can still be taught explicitly.

To save a calculation that follows future corrections, teach examples for
its target phrase, then run `out/heed compose FILE "sum of SOURCE" "sum of TARGET"`
using the taught words. Mind fits a small integer expression to the source
outputs and target answers. The lesson log records the expression and the
source phrase it calls. On the next `memory use` or Mind lesson import, Pi
rebinds saved calculations in dependency order and checks their target
observations. An unresolved source or a conflicting target lesson withholds
the calculation and its dependents. Saved formulas support integer constants,
the source value, addition, subtraction, multiplication, minimum and maximum.

When the specialized learners exhaust their explanations, Heed sends the
original input/output pairs to Mind. Mind searches with the current base
vocabulary and no held-out answers. It tries to find a rival of comparable
size that also fits the lessons but disagrees on an unlabelled probe. When
it finds one, Heed asks for the probe answer and withholds the vocabulary
export. Otherwise the result is a bounded-search hypothesis. Lesson import
rebuilds these hypotheses from the observations before replaying named
compositions. The fallback uses at most five units of uniform program size
for forward search and a cap of 30,000 retained forms per search.

If a subsequent target lesson contradicts a saved composition, Heed keeps its
arithmetic and tries switching between its original source and another resolved
list-to-integer skill. It considers even/odd length and cutoffs at observed
lengths. Each branch needs an example the other source gets wrong. Heed asks
for a distinguishing example when repairs disagree. Replay exports a revised
rule only when one candidate remains, then checks dependent calculations against
their own observations. The lesson log preserves the original recipe and the
evidence for the revision.

The preservation property follows from the update itself. Write an input as
`x = [first, last]` and let the rows of the invertible matrix `P` be the two
anchors. For a candidate neuron `z(x) = max(0, first - last - k)`, solve
`P c = [z(anchor1), z(anchor2)]`. Its correction feature is `g(x) = z(x) - x·c`.
It is zero at both anchors. At a missed lesson with nonzero `g`, adding
`(target - prediction) * g(x) / g(missed)` fixes that lesson while preserving
the anchors. The implementation uses integer determinants, folds the correction
into a single Mind expression, and checks the other lessons by executing it.

Run `out/heed review out/lessons.txt` to use that memory in the ordinary Heed curriculum.
When practice examples support multiple readings, Heed can save them and ask for a distinguishing
example. Answer with `teach` and rerun `review` to see how the correction transfers.

When a `use` request has several possible answers, Heed tries questions on other small
lists. It chooses a question that minimizes how many different answers to your original
request could remain after the reply. Teach the reply and repeat the original request.
Different meanings can agree on that request and still disagree on a later one.

For example, teach that the product of “vems” on `0` is `0`, then ask for the product
on `4,5,6`. Heed asks for the product on `3,5,7`. If you teach `-105`, it can answer
`-120` on the original list while it still needs another observation for `7,8`.

Run `./build.sh examples/native/inquiry.pi` and `out/inquiry compare` to compare
the two question policies. It prints the number of ambiguous requests, the number
of request/rule pairs, and how many each policy resolves with one reply.

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
