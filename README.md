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

In the same chat, teach spatial operations by showing input and output grids.
Separate columns with commas and rows with slashes.

```text
Navo maps grid 1,1/2,3 to 1,1/3,2.
Zemi maps grid 1,1/2,3 to 1,2/1,3.
Apply navo, then zemi to grid 1,2,3/4,5,6.
Reverse the order.
```

The two results are `[[3, 6], [2, 5], [1, 4]]` and `[[4, 1], [5, 2], [6, 3]]`.
Chat keeps the last successful transformation and its original input during the
conversation. The learned operations persist alongside arithmetic lessons in
`out/chat_lessons.txt`. Heed can use that same file with `heed grid`.

Teach a list operation with `Biggest first maps list 2,1,3 to 3,2,1.`
Then `Apply biggest first to 4,9,1.` returns `[9, 4, 1]`. Chat reads a flat
input as a list and slash-separated rows as a grid. Specify `to grid` for
a single-row grid. A phrase can have a different learned meaning for each
input type. Both support sequences and the follow-up `Reverse the order.`

### Other capabilities in chat

Start chat from the repository root after building it with the normal build
script. These turns use the existing notebook, Tongue, trace planner, research
program, and screen reader.

| Chat turn | Result |
| --- | --- |
| `Remember that my telescope is called Juniper.` | Saves a notebook entry available across sessions and through `--recall`. |
| `Recall my note about the telescope.` | Retrieves matching entries. |
| `Teach language dax => RED` | Saves a phrase and its meaning. A later example with the same phrase corrects it. |
| `Interpret dax twice` | Uses Tongue's rules induced from your examples. Teach examples of “twice” first. |
| `Plan goal 1 &#124; out/queue.obs` | Finds an action sequence from a trace log, or requests a missing observation. An optional third field supplies events already taken. The first line of the log is `events` followed by the alphabet. Subsequent lines contain an outcome (0 or 1) followed by its events. |
| `Research Who discovered Ceres?` | Runs the research program and returns its answer and evidence when available. |
| `Read the screen` | Runs Look on the runtime's screen. Linux uses the modeled desktop. |
| `List programs` | Discovers native source files with a main entry point in this checkout. |
| `Run program tongue &#124; mini` | Compiles and runs the named entry point. Each field after the name is one argument. |
| `Remember that result` | Saves the last program, planning, or language reply to the notebook. |

To plan without preparing a file, say `Plan goal 1 using events on`. Pi asks
for the outcome at reset, then for the outcome of specific sequences starting
from reset. Give each result as `outcome 0` or `outcome 1`. You can ask an
unrelated question and return to the pending experiment. A bare 0 or 1 also
works when no arithmetic clarification is pending. With outcomes 0 at reset,
1 after `on`, and 1 after `on on`, Pi returns `plan on`. Ask `Plan goal 0`
to reuse those observations. A bare `plan` means the starting state already
meets the goal. The inferred model and its observations belong to this chat
session; `Cancel plan` clears them. When starting from a trace file, chat
holds a snapshot and keeps subsequent answers in the session.

Say `Find a way to turn on lamp A.` to start a named plan. Pi treats
`on` as the available event and 1 as the desired outcome (`off` uses 0).
To specify other actions, say `Plan goal 1 for lamp A using events press reset`.
Pi checks saved research for each requested trace, cites the source, and
continues planning. It asks for the first missing or conflicting observation,
then resumes when you answer. Ask `What do you need?` to see the exact
observation currently pending. Research and chat deliver answers to the same
request, which carries the operation to resume. Ask `Why will that work?` to see the recorded outcome for the proposed sequence, or whether Pi inferred it from its model. These commands propose actions from reset.

During a planning question, say `Research plan for lamp A` to identify the
system. Pi looks up the exact question about that system and the requested
event sequence. A recorded answer of 0 or 1 with a source and evidence goes
to the planner immediately. Chat shows the evidence and the next question or
plan. Say `Research plan` for the next observation. If the lookup cannot
supply a sourced binary answer, the question stays open for a manual outcome.

Ordinary turns can also use what Pi has learned. Teach a list operation with
`Pivot maps list 2,1,3 to 3,1,2.`, then give the language example
`Teach language kef => pivot`. After restarting chat, `Kef on 4,9,1`
returns `[1, 9, 4]`. Tongue interprets the phrase and Heed evaluates the
operation on the supplied input. Learned phrases can also resolve to a
sequence such as `pivot then pivot`.

For questions the fact engine cannot settle, chat checks saved research for
the same question and includes its recorded source and evidence. If there is
no matching research, it can return related notebook entries as quotations
under a separate label. Explicit `Research` requests still use the research
program.

Program calls use the local compiler under `out/`, share the checkout's working
directory, and return up to 64 KiB of output. They run with the same file, device,
and data requirements as standalone calls. Child programs receive end-of-input
on stdin. Libraries are reached through their callers. Python experiment drivers
on other branches require their own checkout and dependencies.

### Growing a neural curve in chat

`Teach curve tide 0=0 2=3 4=0 6=3 8=0` learns a scalar function with three hidden
ReLU units. Ask `Curve tide neurons` for its size and `Curve tide at 3` for the
exact interpolated value `3/2`. Teaching another value at the same input corrects
that lesson. Names use letters. Each name has its own lesson file under `out/`.
Input and output lessons accept integers from −100,000,000 to 100,000,000.

Pi joins consecutive observations with straight lines. Each change of slope at
a breakpoint contributes one hidden ReLU, weighted by the difference between
successive slopes. The network uses the first line as its affine baseline.
Within the observed range this represents the same function as summing all
those weighted ReLUs. Chat stores the breakpoints and selects the active
segment by binary search. Collinear samples require no extra units. The
learner retains original observations so that a correction can restore a bend.
A single example supports only that input. Predictions outside the taught
range are withheld. A lookup also checks the lesson file for changes.

### A shared recurrent unit for checking predictions

Curve learning and goal planning use one scalar state on Softwell's modeled
SSD. If a later observed integer confirms or contradicts a curve prediction
at the same input, the shared unit updates. A planner probe with a known
model prediction supplies the same feedback. The update moves the estimate
one quarter of the way toward 1 for a surprise or 0 for an agreement, rounded
in units of 1/1024. The neutral initial estimate is 1/2. A feedback log in
`out/chat_neuron.log` restores the state for new chat sessions.

A score over 1/2 enables one extra conformance probe when the planner reports
an unreachable goal. The checker uses a two-state bound to propose that probe;
this is a search heuristic, not a bound on the actual world. A measured cold
Softwell page read during the gate raises the threshold by 1/8. If an observed
sequence reaches the requested goal from the requested prefix, chat can return
that witnessed plan immediately. The same gate asks for an observed value
when chat interpolates a previously untaught curve input.

Use `Neuron status` to inspect the estimate. For example, teach `ramp` with
`0=0 4=4`, ask for its value at 2, and teach the correction `2=3`.
Then say `Plan goal 1 using events press` and reply with outcomes 0, 0 and 1.
The extra experiment discovers `plan press press`. For a switch that always
returns 0, the extra experiment costs one reply without finding a plan.
This estimate tracks recent prediction errors; its value is not a calibrated
probability for a new domain.

### Repair history in chat

Build `examples/native/heed.pi` and `examples/native/chat.pi` and run chat
from the checkout with Python 3 on PATH. Alternate `repair task slow` and
`repair task fast` to run the two bundled resettable dispenser simulations.
The Python driver from the research branch chooses a repair strategy from
paired observation costs stored in `out/repair_history.sqlite`. Once both
diagnostic outcomes have enough support, it buys an early observation only
when the observed savings would cover the cost. Chat reports the chosen
strategy and the number of times the target was actually observed. The
alternative strategy is measured by replay against the verified inferred
table. Only completed pairs update the cost history.

The shared unit breaks a tie between equally costly strategies (a high
surprise estimate favors trying the pattern library). After a paid probe
with a historical majority prediction, its observed bit updates the shared
unit. An even split produces no prediction feedback. To use a custom
simulation, put `repair_NAME.json` in `out/` following the bundled examples.
The target table supplies reset-and-run outcomes; the selector sees only
those observations. The historical database format and context keys match
the research driver; a matching research database can be used at the same
path. These counts measure simulated target interactions.

- **Language, its own way.** `tonguelib.pi` learns a language from example sentences with no network and
  nothing trained: it keeps the smallest set of readable rules that explains everything it heard, and checks
  each rule against all of it. `tongue.pi` measures it on the SCAN benchmark: from the 422 shortest commands
  it reads the other 20,488 correctly, including every sentence the benchmark's splits hold back. `heed.pi`
  uses the same learner on the mind's own tasks: an English instruction Pi was never given is read as a
  program and run. When it is then shown examples for one it got wrong, it checks its own reading against
  them and mends it (a new word, a wrong order) before it falls back on searching.

### Refining a provisional model

The frozen fraction learner merges `acbc` and `aa` into the same rejecting
state. Appending `c` distinguishes them. The action names and binary labels
are the only information supplied to the learner. The optional refiner looks
for short loops that restore a state elsewhere in the inferred table, then
tries inserting them in observed successful traces where the model predicts
failure. On disagreement, native `states-refine` bisects a counterexample
and adds one distinguishing suffix to the observation table. This is an
experimental strategy for spending a remaining observation budget.

Starting with a fresh log, run from the repository root:

```sh
python3 tools/trace_agent.py out/heed out/fraction.obs --events a b c --goal 1 --finish-model --budget 96 --oracle python3 tools/frozen_tasks.py --observe fraction
python3 tools/refine_model.py out/heed out/fraction.obs --budget 96 --oracle python3 tools/frozen_tasks.py --observe fraction
python3 tools/check_refinement.py out/heed
```

The refiner extends the log in place and charges the original observations
against the same limit. It returns a table only when consistent with all
logged observations. On the fraction task the first challenge found a missed
positive at observation 57. The six-state model finished after 75. Excluding
every trace used by either run, positive recall through length seven rose
from 25/78 to 34/78 with zero false positives in both cases. The probe design
was developed after inspecting this task. In a separate twelve-seed panel of
generated finite machines under a 96-query cap, ten runs yielded both models.
Errors on their 7,243 common unseen length-six traces fell from 74 to 12;
all of that improvement came from one seed. One baseline did not finish and
one refinement did not finish. The baseline stops when it finds a consistent
table and can spend fewer observations. These figures do not establish an
advantage over every alternative use of the remaining budget.

For a cost-matched control, keep a copy of the original 56-observation log
before running refinement. Both arms use the focused suffix splitter. Only
the choice of probe differs. The control tries the shortest unseen trace,
and gets exactly the number of observations the targeted arm used, including
refits. The evaluation excludes the union of both training logs.

```sh
python3 tools/check_refinement.py out/heed --fraction-log out/fraction-original.obs
python3 tools/check_refinement.py out/heed --matched --first-seed 100 --machines 48
```

On the fraction task, each arm spent 75 observations total. Of 52 unseen
positive traces of exactly length seven, targeted probes recognized 20 and
the control recognized 14, with zero false positives in either arm. On 48
fresh finite machines, three initial models exhausted the budget. Among the
45 remaining, targeted refinement completed 38 models and shortest-unseen
completed 40. On all 36 paired completions the error counts tied, totaling
130 errors per arm across 26,032 common unseen length-six traces. The
fraction result does not justify preferring targeted probes by default.


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
