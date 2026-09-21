# Open questions

**Boundary:** these are questions a simulation sandbox can help *frame*. Answering any of
them about humans requires human data collected under ethics approval. Nothing here is
medical advice, and no answer here would follow from running the sandbox.

This file has three parts: (1) what the sandbox can genuinely explore, (2) what data human
testing would actually need, and (3) why the sandbox cannot establish causality.

## 1. Questions the sandbox can explore

These are questions about the *model*, not about biology. They are answerable inside the
repository, reproducibly, with the seeded RNG and virtual clock.

| # | Question | How you would explore it | What a result would mean |
| --- | --- | --- | --- |
| Q1 | Under a fixed repair rate, is the final `damage_level` trajectory bounded for all admissible `attention budget` values? | Sweep the budget across its range at fixed seed; inspect for non-monotonicity, oscillation or blow-up | A statement about the *equations*, e.g. whether the conscious term can drive `damage_level` negative. Says nothing about tissue. |
| Q2 | How much of the variance in time-to-threshold is attributable to the stochastic boost versus the deterministic baseline? | Variance decomposition across seeds and parameter draws | A statement about the *model's* sensitivity, not about attention. |
| Q3 | If the boost multiplier is set to 1.0 (no effect), does the model still reproduce the qualitative shape claimed for the original toy? | Run the ablation | A useful honesty check: if the shape survives ablation, the boost was decorative. |
| Q4 | Does the `expectancy` module produce clinically plausible placebos, or does it merely lengthen the tail? | Sweep expectancy parameters with the mediator field as an intermediate | A statement about what the model *assumes* expectancy does, and whether that assumption is internally coherent. |
| Q5 | Is the model identifiable? With the mediator field unobserved, can the same trajectories arise from different (baseline, boost) pairs? | Fit the model to its own synthetic output with the mediator field hidden | If not identifiable, the model cannot distinguish "attention helps" from "baseline was higher". That is a *design* finding, and a useful one. |
| Q6 | How does the attention budget as a finite resource change conclusions once a cost term is added? | Add a cost per unit of attention and re-sweep | A statement about the trade-off structure of the model. |
| Q7 | What happens if the boost can be negative (nocebo branch)? | Sign-flip the module | A statement about whether the model is symmetric, and whether it is honest to present it as purely beneficial by default. |

**Falsifiable in the ordinary sense?** Yes — each question has a definite answer computable
from the code. That is different from the questions in part 2, which are about the world.

## 2. What human data would actually be needed

Anyone wanting to test the *biological* version of the claim needs, at minimum:

1. **A standardised wound model with an objective endpoint.** Human wound models with a
   defensible measurement story exist: punch biopsy, suction blister, tape stripping,
   palate biopsy, and surgical wound assessment. Koschwanez & Broadbent (2011) review the
   options and their pitfalls (pain, cost, inter-rater reliability, tissue-type specificity).
   Ideal: a primary endpoint that a pathologist or algorithm can score blind to condition.
2. **Standardised imaging or histology**, not photography alone. Photographic wound scoring
   is cheap but has substantial inter-rater and lighting variance; if photography is used it
   needs calibrated capture and blinded scoring. See `experimental-design.md`.
3. **A placebo/sham control with matched attention.** The critical design problem: if the
   treatment is "pay attention to the wound", the control must receive the same amount of
   experimenter contact, the same session count, and a plausible task that is not
   wound-directed. Otherwise the study measures attention-plus-ritual-plus-relationship.
4. **Pre-registered expectancy manipulation checks.** Measure what participants believe,
   before and after, with validated scales. Expectation is a confounder *and* a candidate
   mediator; you need both.
5. **Longitudinal confounder data**: sleep (actigraphy), perceived stress and cortisol,
   smoking, alcohol, medication (especially anti-inflammatories and steroids), comorbidity,
   BMI, age, baseline immune function.
6. **Power that reflects realistic effect sizes.** The stress-and-healing literature
   suggests small effects on hard endpoints. That implies large samples for wound closure,
   or more sensitive intermediate endpoints (e.g. cytokine profiles), each with its own
   validation cost.

**None of this exists for this project.** There is no dataset here, no pilot, no protocol
submitted anywhere. Everything above is a shopping list, not a plan that has been executed.

## 3. Why the sandbox cannot establish causality

- **A simulation contains exactly the assumptions that were written into it.** Derivations
  from the code are deductions from assumptions, not observations. This is true even when
  the code is elegant, and even when the output looks like a real healing curve.
- **The parameters are invented.** `healing_rate = 0.5` and a 1.0–3.0 boost have no unit, no
  measurement and no provenance. See `evidence-grading.md`.
- **The direction of the real evidence does not support the model.** The human literature
  supports stress *impairing* healing; the sandbox models attention *improving* it. Absence
  of a brake is not presence of an accelerator.
- **Simulated mediating variables are not measurements.** A "mediator field" whose values
  are produced by the same equations as the output cannot be used to explain the output.
- **No identification and no counterfactual.** The model cannot tell you what would have
  happened with a different amount of attention, because it has no variation it did not
  create itself.

Corollary for anyone writing about this project: it is fine to say the sandbox illustrates
*what an assumption would imply*. It is not fine to say the sandbox *shows* that attention
changes healing, and it is never fine to say it helps anyone.
