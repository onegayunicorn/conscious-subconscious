# Evidence grading

How this project rates claims. Short, deliberately blunt, and applied without
generosity — especially to the project's own assumption.

## The rubric

| Grade | Meaning |
| --- | --- |
| **A** | Systematic review or meta-analysis of randomised controlled trials, with acceptable heterogeneity and low risk of bias. Also: a large, pre-registered, well-blinded RCT that has been independently replicated. |
| **B** | A single adequately powered, adequately blinded RCT; or a meta-analysis that is seriously limited by heterogeneity, small trials or unclear blinding. |
| **C** | Observational human study (cohort, case–control, cross-sectional), or a mechanistic human study (e.g. experimental pain, imaging, biomarker) that does not test a clinical outcome. Also: psychometric validation of a measure. |
| **D** | Mechanistic hypothesis, narrative review opinion, animal/in-vitro extrapolation, simulation output, or unsupported speculation. **Not evidence of an effect in humans.** |

Notes:

- Grades describe the **strength of evidence for the specific claim as stated**, not the
  quality of a paper overall. One paper can support an A-grade claim and a D-grade claim.
- "Mechanistically plausible" always grades **D** unless there is human outcome data.
- Simulation output from this repository grades **D by construction**. A sandbox cannot
  upgrade its own premise.
- Where a claim sits between two grades, the text says so explicitly.

## Grading the claims in the source document

The original input was an AI-generated design conversation (a PDF) containing toy
simulations in Python, Java and JavaScript. It halves `damage_level` each tick and adds a
random "conscious boost" of 1.0–3.0. Every specific claim it makes is graded below.

| # | Claim as made in the source PDF | Grade | Why |
| --- | --- | --- | --- |
| 1 | Baseline healing rate `healing_rate = 0.5` per tick | **D** | No unit, timescale, tissue, organism, measurement or citation. It is a number chosen to make a toy loop look plausible. There is no measurement in any species that licenses "0.5 per tick". |
| 2 | A random "conscious boost" of 1.0–3.0 per tick | **D** | The distribution is invented. The *mechanism* it implies — that attention multiplies a repair rate by an arbitrary factor — has no human outcome evidence. Treating uniform random noise as a model of attention is a mathematical placeholder, not a model of anything. |
| 3 | "Static energy from the brain" directed at the wound | **D** | Not a recognised physiological quantity. No known measurement corresponds to it. This is the weakest claim in the document. |
| 4 | "Chemicals flowing to the area" because of focus | **D** | Vacuously directional and untestable as stated. Real signalling exists (cytokines, growth factors, perfusion; see `literature-review.md`), but the PDF asserts a *causal route from attention to those chemicals to faster repair* that no cited evidence supports. |
| 5 | Focus heals "more than it usually would" | **D** | This is the project's central assumption stated as fact. It is the exact claim the sandbox must not endorse. |
| 6 | The simulation demonstrates the mechanism | **D** | A simulation restates its assumptions. Demonstrating that `damage_level` falls faster when you add a larger boost term is arithmetic, not biology. |

**Summary: every specific quantitative and mechanistic claim in the source PDF grades D.**
None of them is upgraded by anything in this repository. If this tree ever cites a paper,
that paper grades the *literature*, not the PDF's numbers.

## The one claim that grades better — and it is not a healing claim

The source document's *motivation* (people feel that attention matters for recovery) is not
absurd as a subject of study. The adjacent literature contains real, gradable findings —
placebo and nocebo effects, stress-related healing delay, HRV biofeedback — reviewed and
graded in `literature-review.md`. The strongest of these reach **A** and **B**.

That literature does **not** transfer to the PDF's claim. Specifically:

- It is mostly about **self-reported** outcomes (pain, IBS symptom scores), not tissue repair.
- Where tissue repair is measured, the direction of evidence is about **stress impairing**
  healing — the mirror image of "focus improving" it, and not equivalent to it. Removing a
  brake is not the same as adding an accelerator, and the sandbox models an accelerator.
- Effects on self-report do not imply effects on wound closure, and effect sizes for
  patient-reported outcomes do not transfer to biological endpoints.

## How to use this file

When the project describes its own model, the honest formulation is:

> "The model makes one assumption explicit and lets you explore its consequences."

and never:

> "Visualisation heals tissue faster."

The second sentence is a medical claim, it is ungraded because it is unsupported, and this
project does not make it.
