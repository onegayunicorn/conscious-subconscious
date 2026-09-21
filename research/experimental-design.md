# Experimental design sketch: attention-modulated healing

**Status: a design sketch, not a protocol.** It has not been submitted to an ethics
committee, pre-registered, funded or run. No part of it has been executed by this project,
and this project has no clinical capability, no clinicians and no data. It is written to
show what would be required, and to make the gap between the sandbox and a real study
concrete.

**Boundary:** this document is a methods exercise for an educational modelling project. It
is not medical advice, not a treatment recommendation, and not a claim that the intervention
described has any effect.

## 1. The hypothesis, stated so it can fail

> **H1.** In healthy adults with a standardised, experimentally induced superficial wound,
> a structured attention-to-wound intervention delivered over N sessions changes the rate of
> wound repair at a pre-specified timepoint, compared with a matched sham-attention control.

> **H0.** There is no difference between conditions on the primary endpoint.

A useful secondary hypothesis, and arguably the more interesting one:

> **H2.** Any observed difference is mediated by expectancy rather than by attention
> itself. Operationalised as: condition effects shrink substantially when post-randomisation
> expectancy scores are included as covariates.

**A prior warning.** H1 is not implied by the sandbox, and the sandbox is not evidence for
it. The adjacent literature that could support it is about *self-reported* outcomes
(placebo, anxiety) and about *stress impairing* healing. There is no well-powered,
well-blinded trial showing that deliberate attention to a wound speeds its closure. Anyone
proposing such a trial should expect a null result and design accordingly.

## 2. Design

- **Parallel-group, randomised, single-blind (assessor-blind), sham-controlled** trial with
  three arms:
  1. **Attention arm** — structured daily attention-to-wound task (guided, timed, logged).
  2. **Sham-attention arm** — identical duration, setting, technology and experimenter
     contact; attention directed at a neutral target (e.g. a matched non-wound skin site, or
     a relaxation task with no wound focus).
  3. **No-contact arm** — standard care information only, to estimate the ritual/contact
     component. (Optional, but without it the sham arm's value is limited.)
- **Allocation:** stratified randomisation (by age band, sex, smoking status) with
  allocation concealment; sequence generated independently of the enrolling investigator.
- **Blinding:** participants cannot be blinded to whether they attend to their wound.
  Assessors of the primary endpoint **must** be blinded, and blinding success must be
  reported. See Schulz & Grimes (2002) for the standard taxonomy.
- **Pre-registration:** public, time-stamped, before first enrolment, with the primary
  endpoint, analysis plan and stopping rules fixed in advance. See Nosek et al. (2018).

## 3. Wound model and outcome measures

**Wound model.** Standardised acute wound with a well-documented measurement history
(Koschwanez & Broadbent, 2011): options include suction blister, tape-stripping, small punch
biopsy, or `ePTFE` tube implantation for a biochemical endpoint. Trade-offs: pain and
acceptability, ethical burden, tissue-type specificity, and whether the endpoint is
structural (closure) or biochemical (exudate cytokines). Choice must be justified against
the hypothesis, not against convenience.

**Primary endpoint (one only, pre-specified):** a blinded, quantitative measure of repair at
a fixed timepoint — e.g. percentage re-epithelialisation of a standardised wound assessed
from calibrated, colour-referenced photography scored by two blinded raters, with
disagreements adjudicated.

**Secondary endpoints:**
- Histology (blinded pathologist), if biopsy is used.
- Validated patient-reported outcomes: pain (e.g. a validated numerical rating scale with
  defined anchors), function, wound-related distress.
- Biochemical: local cytokine/growth-factor profile from wound fluid.
- **Expectancy and credibility** questionnaires, pre- and post-intervention.
- Autonomic measures (heart-rate variability, respiratory rate) if a breathing component is
  included, and only as secondary — see the caveat in `literature-review.md` §6 that
  blinding is impossible for breathing interventions.

**Explicitly not endpoints:** any claim about long-term scarring, infection rates,
post-surgical recovery in patients, or any diagnostic/treatment outcome. Those would require
a different study with a clinical population and regulatory considerations, and this sketch
does not cover them.

## 4. Measurement pitfalls to state up front

| Pitfall | Mitigation |
| --- | --- |
| Photographic scoring is lighting- and rater-sensitive | Calibrated capture rig, colour reference card, two blinded raters, report inter-rater agreement (ICC) |
| Wound area is a crude proxy for repair | Combine structural and biochemical endpoints; do not treat area as mechanism |
| Small wounds heal nearly completely in healthy volunteers (ceiling effect) | Choose a timepoint before ceiling; pilot to confirm dynamic range |
| Condition unblinding leaks into self-report | Blind assessors; pre-register which outcomes are self-reported and interpret them separately |
| Individual differences in baseline healing dominate | Stratified randomisation; baseline covariates in the analysis plan |

## 5. Confounders to measure, not just mention

Sleep duration and quality (actigraphy where feasible), perceived stress and, if measured,
cortisol, smoking and alcohol, medication (especially NSAIDs, steroids, immunosuppressants),
comorbidity (diabetes), BMI, age, sex, physical activity, and expectation/credibility.
Randomisation does not remove these at small sample sizes — measure them and pre-specify
covariates.

## 6. Ethics

- **IRB/ethics approval before any participant contact**, with the wound model's pain and
  infection risk honestly described.
- **Informed consent must not oversell.** Telling participants that attention heals wounds
  would be a false statement, and it would itself generate a placebo effect and an
  uninterpretable trial. The consent document must say the mechanism is unproven and that
  the study is designed to detect whether an effect exists at all.
- **Nocebo risk.** Describing wounds and healing can increase symptom reporting. The
  nocebo literature (Colloca & Miller, 2011) should shape wording.
- **Data protection and pre-specified analysis**, including how many primary analyses will
  be run and what happens if the primary endpoint is missing.
- **Vulnerable populations excluded** at first; no claims extrapolated to patients.

## 7. Analysis plan sketch

- Intention-to-treat as the primary analysis; per-protocol as sensitivity.
- Primary comparison: attention vs sham, on the single pre-specified endpoint, with a
  pre-specified covariate set; report effect size and confidence interval, not just *p*.
- Pre-specified mediation analysis for the expectancy pathway (H2), with the standard
  caveat that mediation from observational intermediate variables cannot establish
  causation.
- Multiplicity: pre-specify family of secondary outcomes and control, or label all
  secondaries exploratory.
- Report: the randomisation sequence generation, allocation concealment, blinding of
  assessors, and all deviations.

## 8. What this sketch is not

It is not a protocol, not an approved study, not a pilot, and not evidence. It is the
document the project would have to hand to an ethics committee *before* it could legitimately
say anything about attention and healing in humans. Until then, the sandbox's own claim
remains what it has always been: an assumption, made explicit, explored in a simulation.
