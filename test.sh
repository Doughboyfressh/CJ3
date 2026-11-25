#!/bin/sh
# The Linux suite: what test.cmd checks on Windows, with the Linux compiler (seed/pic).
#   1. The self-compile fixpoint: the seed builds the compiler, which builds itself, which builds itself again;
#      the last two must be the same file, byte for byte.
#   2. The two systems agree: the Linux compiler cross-compiles the Windows compiler, and it must be seed/pic.exe.
#   3. Every program with a golden file is compiled, run, and its output compared byte for byte -- the same golden
#      files Windows is held to. gpu for runs on the software chip, so it is not skipped. Programs that still
#      need a Windows-only facility are listed in WINDOWS_ONLY and skipped.
#   4. The agent remembers across runs.
cd "$(dirname "$0")" || exit 1
mkdir -p out
WINDOWS_ONLY=""
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
  } > out/t_heed_memory.txt
  if cmp -s out/t_heed_memory.txt examples/native/golden/heed_memory.expect; then echo "ok   Heed transfers corrections across runs"; else echo "FAIL Heed lesson memory"; fail=1; fi
fi
# Exercise both native dialogue entry points with an isolated profile.
(
  set -e
  profile=$(mktemp -d)
  trap 'rm -rf "$profile"' EXIT
  mkdir "$profile/out"
  root=$PWD
  out/t_g2 examples/native/chat.pi "$profile/chat" >/dev/null
  out/t_g2 examples/native/ask.pi "$profile/ask" >/dev/null
  cd "$profile"
  ./chat < "$root/examples/native/golden/agent_teach.in" >/dev/null
  ./chat < "$root/examples/native/golden/agent_recall.in" > recall.txt
  cmp recall.txt "$root/examples/native/golden/agent_recall.expect"
  [ "$(./ask "Who is Ann's grandparent?")" = "Tom is Ann's grandparent." ]
  [ "$(./chat --remember violet)" = "saved (1 notes)" ]
  [ "$(./chat --recall violet)" = "violet" ]
  printf '%s\n' 'The sum of nells for 2 and 3 is 10.' '24.' | ./chat > lesson.txt
  grep -Fx 'What is product of nells on 2,3?' lesson.txt
  grep -Fx 'Learned nells: (e * 2) before reduction.' lesson.txt
  printf '%s\n' "What's the product of nells for 2, 4, and 6?" | ./chat > answer.txt
  grep -Fx '384. I applied (e * 2) to each input, then took the product of 4,8,12.' answer.txt
  printf '%s\n' 'The product of vems for 0 is 0.' 'What is the product of vems for 4,5,6?' | ./chat >/dev/null
  # Simulate a partial journal append between processes.
  printf '\nWhat is sum of invalid' >> out/chat_questions.txt
  printf '%s\n' "Who is Ann's grandparent?" '-105' | ./chat > resumed.txt
  grep -Fx 'What is product of vems on 3,5,7?' resumed.txt
  grep -Fx "Tom is Ann's grandparent." resumed.txt
  grep -Fx -- '-120' resumed.txt
  [ "$(./chat </dev/null)" = "Goodbye. I know 6 facts." ]
  printf '%s\n' 'The sum of novs for 2 and 3 is 10.' | ./chat >/dev/null
  printf '%s\n' cancel | ./chat > cancelled.txt
  grep -Fx 'Question cancelled.' cancelled.txt
  [ "$(./chat </dev/null)" = "Goodbye. I know 6 facts." ]
  printf '%s\n' 'Navo maps grid 1,1/2,3 to 1,1/3,2.' | ./chat > spatial.txt
  grep -Fx 'Learned navo as gfliph(_).' spatial.txt
  "$root/out/t_heed" grid out/chat_lessons.txt teach zemi 1,1/2,3 1,2/1,3
  printf '%s\n' 'Apply navo, then zemi to grid 1,2,3/4,5,6.' 'Reverse the order.' | ./chat > sequence.txt
  grep -Fx '[[3, 6], [2, 5], [1, 4]]' sequence.txt
  grep -Fx '[[4, 1], [5, 2], [6, 3]]' sequence.txt
  [ "$(./chat memory out/chat_lessons.txt use 'product of nells' 2,4,6)" = "384" ]
  printf '%s\n' 'Navo maps list 2,1,3 to 3,2,1.' | ./chat > list-lesson.txt
  grep -Fx 'Learned navo as rev(sort(_)).' list-lesson.txt
  [ "$("$root/out/t_heed" order out/chat_lessons.txt use navo 4,9,1)" = "[9, 4, 1]" ]
  printf '%s\n' 'Apply navo to list 4,9,1.' 'Apply navo then reverse to 4,9,1.' 'Reverse the order.' 'Apply navo to 1,2/3,4.' | ./chat > shapes.txt
  printf '%s\n' '[9, 4, 1]' '[1, 4, 9]' '[9, 4, 1]' '[[2, 1], [4, 3]]' 'Goodbye. I know 6 facts.' > shapes.expect
  cmp shapes.expect shapes.txt
  ln -s "$root/examples" examples
  ln -s "$root/out/t_g2" out/pic
  printf '%s\n' 'events on' '0' '1 on' '1 on on' > light.obs
  printf '%s\n' 'Demo? ||| Juniper ||| local ||| Telescope log' > out/research.kb
  printf '%s\n' 'Remember that Juniper is a telescope.' 'Teach language dax => RED' 'Teach language dax twice => RED RED' 'Teach language lug => BLUE' 'Teach language lug twice => BLUE BLUE' 'Teach language zup => GREEN' | ./chat >/dev/null
  printf '%s\n' 'Recall my note about the telescope.' 'Interpret zup twice' 'Plan goal 1 | light.obs' 'Research Demo?' 'Run program tongue | mini' 'Run program ../missing' | ./chat > programs.txt
  grep -Fx 'Juniper is a telescope.' programs.txt
  grep -Fx 'GREEN GREEN' programs.txt
  grep -Fx 'plan on' programs.txt
  grep -Fx 'evidence: Telescope log' programs.txt
  grep -Fx '  new sentences: 10 of 10 read rightly' programs.txt
  grep -Fx "Unknown native program. Ask 'list programs' from the Pi checkout." programs.txt
  printf '%s\n' 'Pivot maps list 2,1,3 to 3,1,2.' 'Teach language bim => sort' 'Teach language zor => reverse' 'Teach language kef => pivot' 'Teach language bim again => sort then sort' 'Teach language zor again => reverse then reverse' | ./chat >/dev/null
  printf '%s\n' 'Kef again' 'Kef on 4,9,1' 'Kef again on 4,9,1' 'Which telescope is mine?' 'Demo?' "Who is Ann's grandparent?" 'Unrelatedxyz?' | ./chat > coordinated.txt
  printf '%s\n' 'pivot then pivot' '[1, 9, 4]' '[4, 9, 1]' 'Related notebook entries:' 'Juniper is a telescope.' 'Juniper' 'evidence: Telescope log' 'source: local' "Tom is Ann's grandparent." "I don't understand that yet." 'Goodbye. I know 6 facts.' > coordinated.expect
  cmp coordinated.expect coordinated.txt
  printf '%s\n' 'Plan goal 1 using events on' 'outcome 0' "Who is Ann's grandparent?" 'outcome 2' '1' '1' 'Plan goal 0' 'Cancel plan' 'outcome 1' | ./chat > planning.txt
  printf '%s\n' 'Starting from reset, what is the outcome before any events? Reply outcome 0 or outcome 1.' 'Starting from reset, what is the outcome after on? Reply outcome 0 or outcome 1.' "Tom is Ann's grandparent." 'Give outcome 0 or outcome 1.' 'Starting from reset, what is the outcome after on on? Reply outcome 0 or outcome 1.' 'plan on' 'plan' 'Plan cleared.' 'There is no pending planning observation.' 'Goodbye. I know 6 facts.' > planning.expect
  cmp planning.expect planning.txt
  printf '%s\n' 'For lamp A, starting from reset, what is the outcome before any events? ||| 0 ||| bench log ||| Lamp dark at reset' 'For lamp A, starting from reset, what is the outcome after on? ||| 1 ||| bench log ||| Lamp lit after on' 'For lamp A, starting from reset, what is the outcome after on on? ||| unknown ||| bench log ||| No reading' >> out/research.kb
  printf '%s\n' 'Plan goal 1 using events on' 'Research plan for lamp A' 'Research Demo?' 'Research plan for lamp B' 'Research For lamp A, starting from reset, what is the outcome after on?' 'Research plan' 'outcome 1' 'Research plan' | ./chat > research-plan.txt
  grep -Fx 'evidence: Lamp dark at reset' research-plan.txt
  grep -Fx 'This plan is already researching lamp A.' research-plan.txt
  grep -Fx 'evidence: Lamp lit after on' research-plan.txt
  grep -Fx 'Starting from reset, what is the outcome after on on? Reply outcome 0 or outcome 1.' research-plan.txt
  grep -Fx 'The plan still needs a sourced binary outcome.' research-plan.txt
  grep -Fx 'plan on' research-plan.txt
  grep -Fx 'There is no pending planning observation.' research-plan.txt
  printf '%s\n' 'For lamp A, starting from reset, what is the outcome after on on? ||| 1 ||| bench log ||| Lamp remained lit' >> out/research.kb
  printf '%s\n' 'Find a way to turn on lamp A.' | ./chat > auto-plan.txt
  grep -Fx 'source: bench log' auto-plan.txt
  grep -Fx 'evidence: Lamp remained lit' auto-plan.txt
  grep -Fx 'plan on' auto-plan.txt
  printf '%s\n' 'For lamp A, starting from reset, what is the outcome after on? ||| 0 ||| second log ||| Lamp stayed dark' >> out/research.kb
  printf '%s\n' 'Plan goal 1 for lamp A using events on' 'outcome 1' 'Find a way to turn on lamp B.' | ./chat > resumed-goal.txt
  grep -Fx 'Sources disagree: For lamp A, starting from reset, what is the outcome after on?' resumed-goal.txt
  grep -Fx 'plan on' resumed-goal.txt
  grep -Fx 'Starting from reset, what is the outcome before any events? Reply outcome 0 or outcome 1.' resumed-goal.txt
  printf '%s\n' 'Teach curve wave 8=0 0=0 2=3 6=-3 4=0' | ./chat > trained.txt
  grep -Fx '5 samples, 2 hidden ReLU neurons.' trained.txt
  printf '%s\n' 'Curve wave at 5' 'Curve wave at 8' 'Curve wave at 9' 'Teach curve wave 2=0 6=0' 'Teach curve wave 3=9 bad' 'Curve wave at 3' | ./chat > curves.txt
  printf '%s\n' '-3/2' '0' 'Outside the taught range.' '5 samples, 0 hidden ReLU neurons.' 'Use integer X=Y lessons between -100000000 and 100000000.' '0' 'Goodbye. I know 6 facts.' > curves.expect
  cmp curves.expect curves.txt
  printf '%s\n' 'Plan goal 1 using events press' '0' '0' | ./chat > baseline.txt
  grep -Fx 'Goal unreachable in learned model.' baseline.txt
  printf '%s\n' 'Teach curve ramp 0=0 4=4' 'Curve ramp at 2' 'Teach curve ramp 2=3' | ./chat >/dev/null
  printf '%s\n' 'Plan goal 1 using events press' '0' '0' '1' 'Neuron status' | ./chat > transfer.txt
  grep -Fx 'plan press press' transfer.txt
  grep -Fx 'Shared surprise estimate: 736/1024.' transfer.txt
  printf '%s\n' 'Plan goal 1 using events press' '0' '0' '0' 'Neuron status' 'Curve ramp at 3' | ./chat > constant.txt
  grep -Fx 'Goal unreachable in learned model.' constant.txt
  grep -Fx 'Shared surprise estimate: 552/1024.' constant.txt
  grep -Fx '7/2. Can you check it? Teach curve ramp 3=VALUE with the observed integer.' constant.txt
  ln -s "$root/tools" tools
  ln -s "$root/out/t_heed" out/heed
  printf '%s\n' 'repair task slow' 'repair task fast' 'repair task slow' 'repair task fast' | ./chat > calibration.txt
  printf '%s\n' 'repair task slow' 'repair task fast' | ./chat > recurring.txt
  grep -Fx 'library repair; checked under supplied bound; 32 target observations; 4 prior verified comparisons.' recurring.txt
  grep -Fx 'Paid diagnostic: c b -> 0' recurring.txt
  grep -Fx 'ordinary repair; checked under supplied bound; 54 target observations; 5 prior verified comparisons.' recurring.txt
  grep -Fx 'Paid diagnostic: c b -> 1' recurring.txt
  printf '%s\n' 'What is the product of nells for 2 and 3?' 'No, it should be twelve.' 'No, it should be 12.' 'What is the product of nells for 3,5,7?' | ./chat > corrected.txt
  grep -Fx 'Give a whole-number correction.' corrected.txt
  grep -Fx '210. I took the product first, then applied (e * 2).' corrected.txt
  printf '%s\n' 'What is the product of nells for 4 and 5?' "Who is Ann's grandparent?" 'The correct answer is 30.' | ./chat > grounded.txt
  grep -Fx '40. I took the product first, then applied (e * 2).' grounded.txt
  grep -Fx 'Which result? Give the word, inputs, and corrected answer.' grounded.txt
  ./chat memory lessons teach "sum of ravels" 2,3 10 >/dev/null
  "$root/out/t_heed" memory lessons teach "product of ravels" 2,3 24 >/dev/null
  [ "$(./chat memory lessons use "product of ravels" 3,5,7)" = "840" ]
)
if [ "$?" = 0 ]; then echo "ok   native chat and ask share persistent facts"; else echo "FAIL native dialogue integration"; fail=1; fi
if [ "$fail" = 0 ]; then echo "ALL PASS: fixpoint and $n programs"; exit 0; fi
echo "SOME FAILED"
exit 1
