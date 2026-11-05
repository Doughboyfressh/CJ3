# The Pi language

Pi is a compiled language written in itself. `examples/pic.pi` is the compiler, a Pi program that compiles Pi
source to a native Windows x64 executable, and it compiles itself. `examples/native/rt.pi` is the runtime
(memory, text, lists, maps, numbers, files, printing), also Pi, compiled into every program. There is no Rust
and no interpreter: the Rust interpreter that bootstrapped Pi was retired on 2026-10-31 (it is kept, not run,
in `C:\Users\Dough\pi_removed\pi_native\`).

## Building and testing

```
build.cmd                     build out\pic.exe (the compiler) from examples\pic.pi
build.cmd prog.pi             compile prog.pi -> out\prog.exe
build.cmd prog.pi out.exe     compile prog.pi -> out.exe
build.cmd reseed              after editing pic.pi or rt.pi: run the tests, then make the new compiler the seed
test.cmd                      the test suite
```

- `seed\pic.exe` is the compiler that starts every build. It is the self-reproducing fixpoint: compiled from
  `examples\pic.pi`, it rebuilds itself byte for byte.
- `test.cmd` does two things:
  - It checks that fixpoint, building the compiler three times in a row and requiring the last two builds to
    be identical.
  - It compiles every program that has a golden file in `examples\native\golden\` and compares its output
    byte for byte. The golden outputs were recorded while the interpreter still existed, and matched it.
- A compiled program prints what `main` returns, then exits 0. `fail(msg)` prints the message and exits 1.

## Syntax

```pi
import "lib.pi"                       # another file's skills, read once, relative to this file

skill name(a, b) -> Any {             # a function; main() is the program's entry
  let x = a + 1                       # bind; inside a block it rebinds the outer name
  if x > 2 { return x } else if x == 2 { return 0 } else { do fail("too small") }
  for item in [1, 2, 3] { let x = x + item }
  for i in range(0, 10) { let x = x + i }
  while x < 100 { let x = x * 2 }
  let f = fn(y) => y * x              # a function value; it captures the names it uses, by value
  let g = fn(y) { return y + 1 }
  return {"total": f(2), "items": [a, b], "label": "x is " ++ x}
}
```

| Form | Meaning |
|---|---|
| `42`, `3.14`, `1.5e3` | an integer, a real |
| `"text"` | text, ASCII, escapes `\n \t \r \" \\ \/` |
| `[a, b]`, `{"k": v}` | lists, maps (keys are quoted text in a literal) |
| `null`, `true`, `false` | `true` and `false` are the integers 1 and 0 |
| `x[i]`, `m["k"]` | indexing; a negative list index counts from the end; a missing one is `null` |
| `+ - *` | arithmetic, integer if both sides are integers, else real |
| `/` | division, always real (`6 / 2` is `3.0`) |
| `//`, `%` | floored division and remainder |
| `^` | power (integer exponent) |
| `++` | joining: lists with lists, anything else as text (`"n = " ++ 5`) |
| `== != < <= > >=`, `and or not` | comparison (1 == 1.0), short-circuit logic |
| `fn(a) => e`, `fn(a) { ... }` | function values; call one as `f(x)` |

`reach { ... }` declarations are accepted and ignored.

## Words

| Area | Words |
|---|---|
| Data | `len str num contains put append slice chars ord keys values has get split join trim lower upper reverse sort sum abs min max format range` |
| Functions | `map(xs, f)` `filter(xs, f)` `reduce(xs, f, start)` `apply(f, args)` |
| Math | `sqrt floor ceil round exp log log10 log2 sin cos tan atan` |
| Files and the command line | `read_file write_file print arg input` (`input()` is the next line of standard input, null at the end) |
| Memory | `mark() release(m, keep) memused()` |
| Values | `typeof(x)` -- "null" "text" "list" "map" "int" "fn" "real" |
| Stopping | `fail` |

Some words behave in ways worth knowing:
- `contains(text, part)` ignores case; `contains(map, k)` is `null`; `contains(list, x)` is membership.
- `has(x)` is `x != null`. `get` works like indexing, but `get(text, i)` gives `null`.
- `split(s)` splits on whitespace runs. `split(s, sep)` keeps empty pieces. `join(xs)` and `join(xs, sep)`
  write each item as text.
- `sort` is stable: two numbers sort by value, anything else by its text.
- `min` and `max` take any number of arguments. They give the first extreme among the numbers, or `null` if
  there are none.
- `format("{} has {}", a, b)`: each `{}` takes the next value as text.
- `num(text)` reads an integer (decimals are not read yet).
- `round` rounds half to even.
- `sqrt` and `round` are exact. `exp`, `log`, `sin`, `cos`, `tan` and `atan` are Pi's own series, accurate to
  about 1e-12. `sqrt` or `log` of a value out of range gives `null`.
- `str` of a real prints a whole number like an integer; otherwise it rounds to six decimals.
- `write_file(path, text)` writes text; `write_file(path, [byte, ...])` writes raw bytes. `arg(k)` is the k-th
  command-line word.

## Modules and programs (`examples/native/`)

| File | What it is |
|---|---|
| `rt.pi` | the runtime |
| `seqlib.pi` | a sequence solver: polynomial (finite differences), geometric, order-2 recurrences |
| `eqlib.pi` | an equation solver: evaluate an expression, or solve a linear or quadratic equation for x |
| `answer.pi` | `answer(s)` sends a comma list of numbers to the sequence solver and anything else to the equation solver |
| `dreamlib.pi` | program induction: an integer op language with learned macros, exhaustive search, a PRNG, held-out checks |
| `dream.pi` | Pi invents problems, hides them, rediscovers them, and verifies on unseen inputs |
| `grow.pi` | compounding: macros learned from easy dreams solve hard problems the base ops cannot reach |
| `rounds.pi` | the library over rounds: macros of macros, reach on a fixed held-out set growing round by round |
| `curious.pi` | curiosity vs a control: frontier dreams and greedy-cover macro choice, against frequency, over 3 seeds |
| `regions.pi` | region memory checked: identical results, kept values survive, ~470x less memory kept |
| `logic.pi` | the reasoning engine: facts and rules as Pi data (`"?x"` variables), backward chaining, built-ins (eq neq lt le add sub mul not); `ask holds values_of` |
| `english.pi` | English as a front end: grammar as data (typed-slot patterns), morphology, closed-class words, prior-knowledge rules; reading to engine terms, writing back, round-trip check |
| `agent.pi` | Pi the agent: reads lines, decides statement vs question, reasons, replies in English, self-checks every learned fact, refuses contradictions, remembers in a memory file (`out\agent.exe [memory-file]`) |
| `fib loops primes math bench data closures words reals mathx matht seq equation answer` | the tested programs |

## How it runs

- **Values.** An integer n is the machine word 2n+1 and `null` is 0. Text, lists, maps, function values and
  reals are pointers to runtime objects.
- **Code.** It is position-independent, with r15 pointing at the data section. The executable has two
  sections, `.text` (read and execute) and `.data` (read and write), and imports from kernel32 only.
- **Memory.** It comes from a bump allocator with no garbage collector. Regions give it back:
  - `let m = mark()` remembers the allocation point. `let v = release(m, v)` frees everything allocated since
    the mark, keeping only `v` (deep-copied down to the mark, every kind including functions).
  - No other value made since the mark may be used after the release.
  - `memused()` is the heap in use, in bytes.
- **Known limits.**
  - Dividing an integer by zero stops the program.
  - The runtime is Windows x64 only.

## Not yet in Pi

The retired interpreter also had these, kept as Rust source in `pi_removed` and to be rewritten in Pi:
- ARC solving
- the knowledge stores (`fact entity facts holders article relation`)
- tensors and the GPU
- web, browser and desktop control
- the language words (`read parse learn say understand generate`)
- the `formula zebra pick program` solvers
- units and quantities
- `try`/`catch`
- the `type rule decide law tool agent memory knowledge` declarations
- a real exponent in `^`, `atan2`, `hypot`, `asin acos sinh cosh tanh`

The `.pi` files directly in `examples/` (other than `pic.pi`) were written for the interpreter and do not
compile yet.
