# Disclaimer

**This is the canonical disclaimer for conscious-subconscious.** Other documents,
reports, READMEs and assets link here rather than restating it, so that there is
one wording to keep correct.

## Medical and health disclaimer

**EDUCATIONAL AND ARTISTIC SIMULATION ONLY.**

conscious-subconscious is **not a medical device**. It does not diagnose, treat,
cure or prevent any condition, and it provides **no medical advice**.

The model encodes an **UNVALIDATED assumption**: that conscious attention can
modulate a modelled tissue-repair rate. That assumption is **not established
clinical fact**. It has no empirical support — the parameter that carries it is
graded `invented` and the project says so in the same file in which it is used.

**Do not use any output of this project to make a decision about a human body.**

Specifically:

- **No output is a prediction.** Healing times, repair rates and areas under
  damage produced by this project describe a scalar variable inside a simulation.
  They are not predictions about a person, a wound, a surgery or a recovery.
- **No output is clinical evidence.** The numbers come from equations, not from
  participants. Simulation output grades **D** under this project's own evidence
  rubric (`research/evidence-grading.md`) *by construction*: a sandbox cannot
  upgrade its own premise.
- **No output is a diagnosis, a prognosis or a treatment recommendation.**
- **No regulatory clearance exists or is sought.** There is no clinical function
  for a regulator to clear.
- **No clinical partner, dataset, trial or regulatory intent exists.** The project
  has none, and claims none.
- **Nothing here replaces advice from a qualified professional.** If you have a
  health concern, see one.

## What this project is

- A **reproducible simulation sandbox** (MIT, `onegayunicorn/conscious-subconscious`)
  modelling two interacting control processes acting on a damaged tissue model: an
  autonomous **subconscious** homeostatic repair system, and a deliberate
  **conscious** attentional system with a finite attention budget.
- A **worked example of explicit assumption-labelling.** Every numeric constant
  carries a provenance grade. 33 of the 34 default parameters have no empirical
  support, and the project states that in the same paragraph in which it uses them.
- A **teaching artefact.** A virtual clock and seeded random streams make every run
  reproducible and digest-verifiable, so the same numbers come out for everyone.
- An **engineering demonstration**: a Python 3.10–3.13 core package with **no
  third-party runtime dependencies**, a JSON-Schema protocol layer, optional
  read-only hardware adapters, and container/Kubernetes/systemd deployment paths.

## What this project is not

| Not this | Why not |
| --- | --- |
| A medical device | No clinical function, no regulatory clearance, no clinical claim. |
| Clinical evidence | Numbers come from equations, not from participants. |
| Medical advice | Nothing here should inform anyone's health decisions. |
| A healing app | There is no established evidence that attending to a wound changes its repair rate. The model assumes it and labels the assumption as invented. |
| A treatment, therapy or intervention | There is no intervention. There is no output channel to any body. |
| A diagnostic tool | It models one scalar variable and measures nothing. |
| A cognitive architecture | It is a narrow toy model of two interacting control loops. |
| A proof that attention affects the body | A simulation contains the assumptions written into it. |
| A quantified-self product | No accounts, no data collection, no cloud sync. |
| A paid product or subscription | **Payments are not implemented.** There is no pricing, no checkout, no subscription and no payment integration, and none is planned. |
| A validated model | Nothing in it has been fitted to data. |

## On the adjacent literature

Real research exists around this subject, and the project reviews and grades it in
`research/literature-review.md`. Read that file before citing it anywhere.

Its conclusions, in short:

- Placebo and expectancy effects are real and well supported **for subjective,
  self-reported outcomes** such as pain, nausea and symptom severity.
- Psychological stress is associated with **slower** healing in standardised human
  wound models. This is the most directly relevant finding, and it is the *mirror
  image* of this project's assumption: **removing a brake is not the same as adding
  an accelerator**, and the model adds an accelerator.
- HRV and slow-breathing biofeedback has reasonable evidence for **stress and
  anxiety** outcomes. It has no established effect on tissue repair.

None of that literature establishes this project's core assumption, and this
project does not extend its claims. Each theme is graded, and the project's own
assumption is graded **D** in every row of the summary table.

## On hardware

Every shipped device adapter is **read-only with respect to the person wearing the
sensor**. No adapter has a write, send or stimulate method, and
`DeviceCapabilities.bidirectional` defaults to `False`. There is no stimulation
path, no actuation and no way for the simulation to act on a body. That is a
deliberate safety boundary rather than a missing feature.

Connecting a heart-rate monitor or an LSL stream to this project does **not** turn
it into a biofeedback product, a monitor or a medical device. It changes where a
number comes from, not what the number means.

## On the name and the assets

The name `conscious-subconscious` is descriptive of the two modelled processes. It
is not a brand, carries no trademark symbol, and must never be paired with a
tagline that implies treatment. See `media/brand.md` for the asset rules; the short
disclaimer line there travels with every composition.

## Reuse and liability

MIT licensed. You may use, modify and redistribute the code under the terms of
`LICENSE`. It is provided **as is**, without warranty of any kind. The authors and
contributors accept **no liability** for any use, misuse, interpretation or
consequence of this software or of any output it produces — including any decision
made about a human body, any claim made about health, or any reliance placed on a
simulated number.

If you deploy, publish or present this project, this disclaimer travels with it.
