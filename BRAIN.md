# How the brain learns -> what Pi does about it

Research sweep, 2026-11-01. Nobody knows exactly how the brain works; these are the best-supported principles, with how
contested each is, and what each means for Pi's core loop. Sources are listed at the end.

| # | Principle (evidence) | What the brain does | Pi today | Pi next |
|---|---|---|---|---|
| 1 | **Child as hacker / language of thought** (Rule, Tenenbaum, Piantadosi 2020; Ullman & Tenenbaum 2020) | Concepts are programs in a compositional mental language; learning is program induction. | YES: Pi *is* a language; induce/learn/listlearn find the smallest program that explains examples. | One language across all domains (numbers, lists, ...) instead of one program per domain. |
| 2 | **Complementary learning systems** (McClelland, McNaughton, O'Reilly 1995; review 2011; supported) | Hippocampus stores episodes fast and separately; neocortex slowly extracts shared structure by *interleaved* replay, which avoids catastrophic forgetting. | Partly: words are learned from solved tasks. | Episodic memory of every solved task, verbatim; "night" consolidation over ALL episodes at once (interleaved), never only the latest. |
| 3 | **Sleep: synaptic homeostasis** (Tononi & Cirelli; downscaling keeps strong, removes weak; partly contested) | Waking strengthens synapses; sleep scales them down, pruning weak ones and sharpening signal-to-noise. | No: words, once learned, stay forever. | Night downscaling: words no memory uses any more go dormant (out of the search), so the vocabulary stays sharp and the search narrow. |
| 4 | **Learning progress / curiosity** (Oudeyer et al. "progress niches"; IMGEP; Gopnik's exploring child) | Curiosity goes where learning is *improving fastest*: not the mastered, not the hopeless. | Partly (curious.pi greedy cover). | Each day Pi spends its effort on the domain whose solve rate rose most (optimistic for untried). |
| 5 | **Reward / information prediction error** (Schultz; information as reward, Bromberg-Martin, Shohamy) | Dopamine signals the gap between expected and received outcome; learning is driven by that error; information itself is rewarding. | No explicit expectation. | Pi predicts per task whether it will solve it; the surprise (solved when not expected, or the reverse) is logged and steers the curriculum. |
| 6 | **Habits vs planning, arbitrated by uncertainty** (Daw, Niv, Dayan 2005; Keramati 2011) | Fast cached habits when reliable; slow model-based planning when uncertain; actions chunk into sequences. | Words are chunks. | Habit first: a task already in episodic memory is answered from memory (no search); only new tasks pay for planning. |
| 7 | **Predictive processing / free energy** (Rao & Ballard 1999; Friston 2009/2010; generality contested) | Perception is prediction; hierarchical prediction errors, weighted by precision, update the model; action also reduces error. | Every learned program is checked by prediction on unseen inputs (interp.pi). | Keep: nothing counts until it predicts held-out data. |
| 8 | **Working memory is small** (PFC; ~4 items; Miller, Engle) | Executive control holds a few rules; capacity limits what can be combined at once. | Search depth is bounded by size. | Keep the search shallow; depth comes from words, not from a bigger search. |
| 9 | **Core knowledge** (Spelke: objects, agents, number, places, geometry) | Infants start with a few domain priors, not a blank slate. | Grid/ARC work: objects, "me" (arc3.pi). | Primitives per domain = the starting priors; everything else is learned. |
| 10 | **Hebbian learning + sparse codes** (Hebb; Krieg & Triesch; sparse coding for energy) | What fires together wires together; a few active units at a time saves energy. | MDL words merge what co-occurs. | Same mechanism: a word = parts that keep appearing together; sparse = few words used per answer. |
| 11 | **Neuromodulated uncertainty** (Yu & Dayan 2002: ACh expected, NE unexpected uncertainty) | Expected uncertainty slows learning; unexpected change (surprise) resets beliefs. | No. | Later: when a whole domain suddenly fails, raise exploration there. |
| 12 | **Cortical columns / reference frames** (Hawkins; contested, not established) | Many similar modules each model whole objects in their own frame and vote. | No. | Not adopted: evidence too weak. |

## The core loop that follows (mind.pi)
Day: pick the domain with the most learning progress -> answer known tasks from episodic memory (habit) -> search the rest
in the current language (plan) -> every answer must predict unseen examples -> store episodes; log surprise.
Night: replay ALL episodes interleaved -> learn the words that shorten them most (MDL) -> downscale: words nothing uses
go dormant -> save the language. Repeat. Measure on tasks never practised, with and without the words.

## Sources
- Rule, Tenenbaum, Piantadosi (2020) The Child as Hacker - https://pmc.ncbi.nlm.nih.gov/articles/pmid/33012688
- Ullman & Tenenbaum (2020) Bayesian models of conceptual development - https://klab.tch.harvard.edu/academia/classes/BAI/pdfs/UllmanEtAl_AnnRevPsych2020.pdf
- Complementary Learning Systems (O'Reilly et al.) - https://www.academia.edu/109609372/Complementary_Learning_Systems
- Synaptic downscaling / homeostasis - https://pmc.ncbi.nlm.nih.gov/articles/PMC5873548 , https://pmc.ncbi.nlm.nih.gov/articles/PMC3317003
- Oudeyer: IMGEP / learning progress - https://ar5iv.arxiv.org/html/1708.02190 ; editorial https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6978885/
- Information as reward (Marvin & Shohamy) - https://shohamylab.zuckermaninstitute.columbia.edu/sites/default/files/2017-02/Curiosity.pdf
- Dopamine and information seeking (eLife 2020) - https://elifesciences.org/articles/59152 ; Schultz prediction error - https://pubmed.ncbi.nlm.nih.gov/10195164/
- Daw, Niv, Dayan: uncertainty-based arbitration - https://nivlab.princeton.edu/wp-content/uploads/sites/938/2024/02/dawnivdayan2006.pdf ; Keramati - https://pmc.ncbi.nlm.nih.gov/articles/pmid/21637741
- Friston, free-energy principle - https://www.nature.com/articles/nrn2787.pdf ; predictive coding - https://www.fil.ion.ucl.ac.uk/~karl/Predictive%20coding%20under%20the%20free-energy%20principle.pdf
- Miller, the working of working memory - https://ekmillerlab.mit.edu/2014/01/23/the-working-of-working-memory ; PFC review - https://pmc.ncbi.nlm.nih.gov/articles/PMC4677100
- Spelke core knowledge - https://dash.harvard.edu/entities/publication/73120378-c387-6bd4-e053-0100007fdf3b ; Kinzler & Spelke - https://www.harvardlds.org/wp-content/uploads/2017/01/Kinzler_CoreSystemsHumanCog-1.pdf
- Gopnik & Wellman, causal Bayes nets in children - https://pmc.ncbi.nlm.nih.gov/articles/PMC3422420
- Yu & Dayan, ACh/NE uncertainty - https://proceedings.neurips.cc/paper/2002/hash/758a06618c69880a6cee5314ee42d52f-Abstract.html
- Sparse coding / Hebbian energy - https://www.frontiersin.org/10.3389/conf.fncom.2011.53.00090/event_abstract
- Thousand Brains 2.0 (contested) - https://arxiv.org/pdf/2507.05888
- Tsividis et al., theory-based RL (EMPA) - https://arxiv.org/abs/2107.12544v1
