# Pi

Pi is an experimental AI system built in its own self-hosting programming language. Its native learner, Heed, turns examples into executable rules, asks questions when several rules fit, and reuses saved observations on later tasks. The Heed examples below run from a fresh checkout with the bundled compiler.

## How the pieces fit

| Component | Role |
| --- | --- |
| [Heed](examples/native/heed.pi) and [Mind](examples/native/mindcore.pi) | Heed learns from lessons and chooses questions. Mind represents and evaluates the programs that explain those lessons. |
| [Softwell](softwell/README.md) | Pi’s software-defined CPU, GPU, RAM, and SSD. It models execution and data movement on a shared clock, with 64 KB of modeled RAM and an 8 MB modeled SSD. |
| [Compiler](examples/pic.pi) and [runtime](examples/native/rt.pi) | The compiler builds native x64 executables for Linux and Windows, including itself. The runtime supplies text, collections, exact integers, files, and region-based memory management. |

The repository also includes neural models and language-model experiments. The native Heed learning path uses examples, program search, and feedback. For the learning design and language reference, see [BRAIN.md](BRAIN.md) and [LANGUAGE.md](LANGUAGE.md).

Two other experiments approach language learning differently. Tongue induces readable rules from example sentences and evaluates them on SCAN. Langgrow uses compile failures to propose grammar changes and tests them before promoting a new compiler seed. [Tongue](examples/native/tongue.pi) · [Langgrow](examples/native/langgrow.pi)

## Current research

On this branch, you can teach Heed a word and use it in a new calculation. The research branch extends Heed to learn hidden states, plan actions, and choose when to reuse earlier repairs. It includes runnable SQLite, queue, file-store, and simulated-dispenser experiments. [Read the research branch and benchmarks](https://github.com/Doughboyfressh/CJ3/tree/pi/neural-list-router#research-results).

## Native chat

Build `examples/native/chat.pi` and `examples/native/ask.pi` with the build
script for your platform. From the repository root, run `out/chat` and enter
`Tom is Bob's parent.` and `Bob is Ann's parent.` on separate lines. After
ending input, `out/ask "Who is Ann's grandparent?"` answers
`Tom is Ann's grandparent.` Both commands use `out/chat_facts.txt`. Chat
also supports `--remember NOTE` and `--recall QUERY`, which use a separate
plain-text notebook at `out/brain_memory.txt`. On Windows use the .exe files.

In ordinary chat, enter `The sum of nells for 2 and 3 is 10.` Pi asks for
their product. Reply `24`, restart chat, and ask `What's the product of nells
for 2, 4, and 6?` Pi answers 384 and shows the transformed inputs 4, 8, 12.
Chat saves observations in `out/chat_lessons.txt`. Chat also saves its pending question and the original request in
`out/chat_questions.txt`. After a restart it repeats the pending question.
Reply with a signed integer, or type `cancel` to clear it across sessions.
When the clarification settles an earlier question, Pi answers it immediately.

To correct a numeric prediction, reply `No, it should be 12.` Pi records the
corrected result for the same word, operation and inputs, then fits the rule
to the saved observations again. The correction applies to the immediately
preceding prediction in this chat. After changing subjects or restarting,
give the observation explicitly.

Chat uses Pi's native English fact and question grammar. Use `chat memory` with the same arguments as `heed memory` below to teach
and apply executable rules. Both commands share the same lesson reader and
can take turns updating the same file.

## Quick start

From the repository root, build Heed and give it two lessons using a fresh lesson file. The sum alone leaves several explanations for “ravels.” The product distinguishes doubling each element from doubling the final result.

**Linux x64**

```sh
./build.sh examples/native/heed.pi
out/heed memory out/lessons.txt teach "sum of ravels" 2,3 10
out/heed memory out/lessons.txt teach "product of ravels" 2,3 24
out/heed memory out/lessons.txt use "product of ravels" 3,5,7
```

**Windows x64 (Command Prompt)**

```bat
build.cmd examples\native\heed.pi
out\heed.exe memory out\lessons.txt teach "sum of ravels" 2,3 10
out\heed.exe memory out\lessons.txt teach "product of ravels" 2,3 24
out\heed.exe memory out\lessons.txt use "product of ravels" 3,5,7
```

The last command prints **840**. Heed applies the learned rule to the new inputs and multiplies 6 × 10 × 14. Each command starts a fresh process and reads the same lesson file.

Run `./test.sh` on Linux or `test.cmd` on Windows for the compiler self-build and golden-output checks. The build scripts also accept other Pi source files. The compiler supports cross-compilation with `pic SOURCE OUTPUT linux` and `pic SOURCE OUTPUT windows`.

## Teach Heed a word

The [quick start](#quick-start) teaches “ravels” and applies it to a new list. The following examples explore how Heed handles ambiguous lessons and learns more complex rules.

The lesson file stores observations. Repeating the same word, operation, and input with a new
answer corrects that observation. The same file is a Mind lesson: a word with one meaning becomes a building block the search can use, and Softwell runs a program made from it. The learner tries small shifts and scales first. If all of
them fail, it tries a bounded search for a scalar expression and checks it against every saved
example for the word. Supported operations are sum, product, count, largest, and smallest on
nonempty lists of integers.

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

## Local data

The build scripts write generated binaries to `out/`. Local experiments also keep lesson logs, indexes, reference text, and model snapshots there. The bundled bootstrap compilers live in `seed/`; the Heed quick start creates its own lesson log.

## Status

A personal research project. Windows x64 and Linux x64.

On Linux the language, the runtime, files, folders, child processes (`spawn`, `par for`), sockets and the clock
all work, and the whole test suite passes against the same golden files as Windows. Softwell is the machine on
both hosts. There is no NVIDIA driver to load. What is still Windows-only: `http()` (WinHTTP), and the screen,
mouse, keyboard and sound words. A program that reaches for one of those on Linux stops with a message naming it.
