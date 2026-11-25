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

## Research results

The native state learner asks for action sequences and observes their outcomes. Python drivers connect it to resettable programs, compare repair strategies, and count target experiments. A target experiment starts from reset, runs one sequence, and returns an observation.

| Question | Measured result | Reproduce on Linux after the quick start |
| --- | --- | --- |
| Can Pi infer transaction behavior? | Pi chose 43 experiments on an in-memory SQLite database. It learned when a row would survive rollback and reused the observations to remove a committed row. | `python3 tools/trace_inference.py out/heed` |
| Can Pi adapt when two rules change together? | Across 24 action renamings of a file store, adapting a model took 1,860 target experiments. Learning from scratch took 2,520. | `python3 tools/storage_transfer.py out/heed --growth-only` |
| When is an early observation worth its cost? | After four calibration tasks, Pi used 516 experiments on 12 recurring dispenser tasks, including 12 diagnostic probes. Choosing from historical averages took 540. On 18 first-seen tasks, both policies took 726. | `python3 tools/storage_transfer.py out/heed --pattern-only` |

These experiments assume repeatable resets, deterministic behavior, and a supplied action set. Model verification uses a supplied upper bound on states. Counts above measure target interactions; local replay and the cost of acquiring earlier repairs are separate. [Run the process learner](#learn-and-control-a-resettable-process) or [try model transfer](#transfer-a-storage-goal-to-unfamiliar-actions).

### Frozen-learner evaluation

`python3 tools/frozen_tasks.py out/heed` runs four tasks chosen after freezing
the native compiler, learner and Python drivers at
[`0b4b535`](https://github.com/Doughboyfressh/CJ3/commit/0b4b535357c6485edbf50ddb6cf5cd4741e67684).
Each task starts with an empty log. Pi receives three opaque action names,
a goal of 1, and a binary observation after each reset-and-run experiment.
The driver supplies no state bound or worked example. The budget is 96
experiments per cold task. A direct-search baseline tries short traces first.

| Task | First positive / episodes to return a plan | Unseen successful traces recognized |
| --- | --- | --- |
| Emit the euro character with an incremental UTF-8 decoder | 29 / 75 | 9 of 9 |
| Reach 3/2 using doubling, increment and reciprocal | 21 / 56 | 4 of 10 |
| Finish a balanced parenthesis sequence with nesting depth at least two | No positive in 96 | — |
| Match a four-byte BLAKE2s digest | No positive in 96 | — |

Unseen predictions cover all action traces through length five absent from
the training log. Direct search found the first two goals on episodes 29 and
21 and exhausted the budget on the other two. In six directed transfer runs
from the two completed models, the UTF-8 model helped find a fraction plan in
2 episodes versus 21. The remaining five tied direct search, including four
budget exhaustions. These four tasks measure behavior through a supplied
action/feedback interface. They do not establish general intelligence.

To compare the current goal-directed stopping rule on the same tasks, run
`python3 tools/frozen_tasks.py out/heed --first-plan`. It returns the UTF-8
plan after 29 experiments and the fraction plan after 21. Both other tasks
still exhaust 96 experiments. The query order up to success is identical.
These savings come from returning a witnessed solution sooner. The default
evaluation continues to a provisional model for the held-out predictions.

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
Supported mechanisms are `follow`, `latch`, `retry`, `delay`, `sequence`, `rearm`, and `double-reset`.
When count rules contradict recorded crossings or cannot lead to a goal or
experiment, Pi also constructs Mind folds over ordered pairs of event types.
The three templates distinguish a strict first-occurrence order, an ordered
subsequence, and the first event of a pair. Each program is checked against
the raw recorded crossings. Planning uses transition tables evaluated from
the surviving programs. New event files retain every distinct trial history
and its crossing outcome; older files can be replayed as partial evidence.

When every count and order program contradicts the observations, Pi learns
which events to retain and which recent sequences of those events predict
an open door. It tries memory widths one through three over subsets of the
five visible events, preferring shorter memory, then fewer event types. It
keeps tied candidates and treats unobserved contexts as closed. In the
`rearm` simulator, a door attempt arms the next crossing and switching on
clears that permission. Before accepting a rule that one occurrence of an event grants
permanent permission, Pi considers each other visible event as a possible
reset. It discards rivals contradicted by recorded crossings and plans a
reachable crossing where the remaining rival and the current rule disagree.
The transfer check starts with an empty log, scores unseen walks with
`out/heed explore-score TRAIN TEST`, and restores the resulting training log
before each transfer layout. Pi also composes ordered pairs of reset events, including repeated events.
The `double-reset` room clears permission on the second switch-on since the
last door attempt. Verifying persistence against more rivals costs extra
experiments even when the initial rule is correct.

For an automated transfer comparison run `python tools/door_transfer.py out/heed`
after building Heed. Each mechanism is learned in the hall, then exercised in
46 other layouts with and without the event file. Each run starts a fresh
process. Actions include experiments and the final goal route; resetting a
trial is free. The experiment-selection policy gives identification priority
when several rules remain. The timer excludes compilation.

## Learn and control a resettable process

Pi can infer a deterministic finite-state process with a binary observation.
Give it the event names and, optionally, an upper bound on reachable states. Each
experiment starts fresh, applies the requested events, and returns one bit.
Pi uses distinguishing suffixes to separate histories and searches the
learned transition graph for a shortest plan to the requested output.

Run this example against Python's two-slot queue from the repository root:

```sh
python tools/trace_agent.py out/heed out/queue.obs --events put take --bound 3 --goal 1 --prefix put --oracle python tools/trace_inference.py --queue-oracle
```

The first run learns the queue and executes the prefix plus its proposed
plan. Reusing the log permits new goals without repeating known queries.
Use a separate log for each process configuration. The oracle reads a JSON
array of event names on standard input and prints `0` or `1`. Each invocation
must reproduce the same initial state and implement every declared event.
Omit `--bound` for goal-directed learning. When an experiment starts with
the requested prefix and yields the desired output, Pi saves the result
and returns the remaining actions immediately. An empty plan means the
prefix itself achieved the goal. The reply reports `states: null` and
`model_evidence: "observed plan only"` for a plan discovered this way.
To continue to a provisional model, run again on the same log with
`--finish-model`. The earlier observations count toward model learning.

During model search Pi tries a plan,
learns from a failed replay, and broadens its experiments when the current
model cannot reach the goal. A successful replay establishes that particular
plan works. The conformance guarantee requires a valid state bound and
deterministic outputs.
When that bound is loose the number of experiments can grow exponentially.

For several observations per experiment, add `--sensor NAME` and use an
oracle that prints a JSON object containing one 0 or 1 per named sensor.
Pi saves every reading and rebuilds the native learner's evidence for the
chosen goal from the same log. Changing the goal sensor reuses past traces
and requests any missing experiments. For the SQLite example, use events
`insert delete commit rollback`, bound 4, and oracle
`python tools/trace_inference.py --sqlite-sensors`. Goals include `durable`
(row survives rollback), `visible` (row visible now), and `pending_change`
(rolling back would change row visibility). Each returned plan gets a fresh
execution against the selected sensor.

The native commands also work independently. A log starts with
`events put take` followed by lines such as `0` for the initial observation,
or `1 put put` for a trace. `heed states FILE` requests missing observations
and exports a table consistent with the available evidence. The table starts
at state zero, with one row per state containing its output and successor
indices in the declared event order. `heed states-check FILE BOUND` also
requests conformance experiments. `heed states-plan FILE GOAL [PREFIX]`
returns a shortest continuation from a space-separated prefix.
`python tools/trace_inference.py out/heed` independently checks equivalence
by traversing pairs of reachable reference and learned states, and exercises
the queue and an in-memory SQLite database from observations through plan
execution. The SQLite adapter exposes insert, delete, commit, and rollback.
Its observation is whether one row survives discarding pending changes.

### Transfer a storage goal to unfamiliar actions

`python tools/storage_transfer.py out/heed` learns a binary transition
table from SQLite. A second environment implements draft and published
bits in separate files. It exposes opaque event and sensor names. Two
labeled snapshots identify the goal sensor without showing an action
sequence. The transfer planner tries mappings between source and target
actions, selects short target experiments that surviving mappings predict
will succeed, and eliminates mappings after failed predictions. If the
guided search runs out of proposals it explores the remaining sequences
within the depth and episode bounds. A successful plan is executed on
the target. The benchmark checks all 24 action renamings against direct
shortest-first exploration and fresh goal-directed Heed. The source and
target implement the same four-state storage abstraction.

For another resettable target, run `python tools/trace_transfer.py --help`.
Supply a native single-output source log, target event names, a JSON file
of labeled target snapshots, and a command that returns a sensor object
for a JSON action list. The planner infers a single goal sensor and tries
bijections for up to six actions. Its plan-length limit controls the cost
of enumerating potential experiments.

Use `--repair` with `trace_transfer.py` to identify a target with renamed
actions and up to one changed transition. This mode starts from the source
table and keeps the state count, initial state, and binary outputs fixed.
Pi chooses traces that split the surviving tables, reports the minimum edit
count, and returns a representative table once all survivors agree on all
reachable traces. The JSON includes the target event order; the first entry
of each row is its output and the remaining entries are successor states.
The family assumption limits the identification claim. An episode budget
can terminate the search while candidates still disagree.

Run `python tools/storage_transfer.py out/heed --repair-only` to compare
repair with fresh bounded learning. In the changed store, restoring into
an empty draft moves the published bit into the draft and clears the
published copy. The benchmark checks the full inferred behavior against
a separate specification, exercises unseen continuations on real files,
and verifies a recovery action. Unchanged controls use the original copy
semantics under the same action renamings.

When the target may need more states, use `--grow-bound N` in place of
`--repair`. Pi tries redirecting one action to a copy of its originating state. The
copy initially retains the original transitions. It checks the proposed
table using access paths and suffixes that distinguish its states under
the supplied upper bound. If a single change fails, Pi tries one redirected transition composed
with one split on a different transition. It eliminates combinations that
disagree with observations already collected. This second search supports
up to 50,000 generated combinations. If local models fail, the native state
learner reuses all target observations. The JSON field `local_model_verified`
records whether a local model passed conformance checking. `local_edits`
reports its edit count, or null after full inference.
If it finds more states than the source had, the JSON includes pairs of
histories, a shared continuation for each pair, and both measured outputs.
Pairwise differences among five histories establish a five-state lower bound
for deterministic behavior, independently of the upper-bound assumption.
The episode budget covers identification and any additional witness queries.

`python tools/storage_transfer.py out/heed --growth-only` exercises a store
that requires two consecutive publish attempts to release a newly marked
draft. The confirmation flag is hidden from the learner. The benchmark
compares with fresh state learning, checks equivalence to a separate
specification, replays the witnesses, and runs an unchanged control.

A verified single split can be exported with `--grow-bound N --save-pattern FILE`.
On a different system, pass its learned baseline log and `--use-pattern FILE`.
The pattern records a sequence of abstract action roles that reaches the
affected state, the role that enters the copy, and the expected output
before and after the original transition. Pi binds those roles against the
new baseline and tests predictions against fresh target observations. A
rejected pattern falls back to ordinary repair with the observations retained.
The target still needs a resettable deterministic interface, goal examples
and a valid state bound. This format covers single splits.

Run `python tools/storage_transfer.py out/heed --pattern-only` to learn a
pattern on the file store and transfer it to a simulated ticket dispenser
with three baseline states and three actions. The benchmark checks all six
action renamings against ordinary repair using the same learned baseline,
and includes a dispenser that issues tickets immediately.

Repeat `--use-pattern FILE` to supply several saved repairs together. Pi
combines their candidate tables and chooses probes that distinguish their
predictions. After checking the selected model on the target, the JSON
field `matching_patterns` lists the zero-based input indices that explain
the verified behavior. Equivalent explanations can share a result. An
empty list means no saved repair was verified. The ordinary learner then
uses the observations already collected.

The pattern benchmark also learns delayed shutdown from a simulated lamp.
It offers both the lamp and file-store repairs to dispensers with delayed
issue, delayed clearing, or immediate operation. It compares model selection
with both ordinary repair and being handed the applicable pattern.

Add `--cost-history FILE.sqlite` alongside `--grow-bound` and one or more
`--use-pattern` files to let Pi decide whether to consult them. For a new
configuration Pi starts with ordinary repair. On subsequent runs it picks
the strategy with fewer cumulative target experiments on completed pairs.
The history key includes the baseline table, state bound, budget and pattern
collection. It excludes the new target's outcomes. Ties use ordinary repair.

After checking a model, Pi replays the alternative strategy against that
model and records both costs. This spends local computation and requires
no additional target calls. The replay assumes deterministic behavior and
a valid state bound. Incomplete pairs do not update the averages. The
`strategy`, `prior_tasks` and `paired_costs` fields expose the decision and
the evidence added afterward. This policy optimizes target experiments;
donor training and local execution time are separate costs.

With `--diagnostic --cost-history FILE.sqlite`, Pi can buy one reset-and-run
observation before selecting a strategy. On previous verified models it
scores up to 256 candidate traces of zero to three actions. Each possible
output must have occurred on at least two previous tasks. Pi buys a probe
only if branching on its result would have beaten the best fixed strategy
on those cases after charging one experiment per task. It logs the actual
trace and measured bit in `early_observation`, or null when it skips the
probe. The probe consumes one episode from the shared budget; the strategy
then runs from reset. Historical savings estimate future value and depend
on how similar the incoming workload is to earlier tasks.

## Teach Heed a word

The [quick start](#quick-start) teaches “ravels” and applies it to a new list. The following examples explore how Heed handles ambiguous lessons and learns more complex rules.

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

## Local data

The build scripts write generated binaries to `out/`. Local experiments also keep lesson logs, indexes, reference text, and model snapshots there. The bundled bootstrap compilers live in `seed/`; the Heed quick start creates its own lesson log.

## Status

A personal research project. Windows x64 and Linux x64.

On Linux the language, the runtime, files, folders, child processes (`spawn`, `par for`), sockets and the clock
all work, and the whole test suite passes against the same golden files as Windows. Softwell is the machine on
both hosts. There is no NVIDIA driver to load. What is still Windows-only: `http()` (WinHTTP), and the screen,
mouse, keyboard and sound words. A program that reaches for one of those on Linux stops with a message naming it.
