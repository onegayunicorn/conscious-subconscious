# Literature review: what is actually known around the sandbox's assumption

**Boundary:** this is an educational review written for a modelling project. It is not
medical advice, not a systematic review, and not clinical evidence. It exists to keep the
sandbox honest about which parts of its premise touch real research and which parts do not.

Grades (A–D) follow `evidence-grading.md`. Every reference listed here is verified; details
are in `bibliography.bib`. Where a theme is genuinely contested, that is stated rather than
resolved.

## Scope of the search

Narrative search across PubMed/Crossref for: placebo and open-label placebo, expectancy and
conditioning, psychoneuroimmunology, psychological stress and wound healing, interoception,
heart-rate-variability and slow-breathing biofeedback, and nocebo. There is **no** PRISMA
strategy, no dual screening and no risk-of-bias tooling. Treat this as a curated reading
path, not an exhaustive synthesis.

## 1. Placebo and open-label placebo effects

**Reasonably well supported.** Placebo effects are real, measurable, and largest for
patient-reported outcomes such as pain, nausea and IBS symptom severity. Open-label
placebo — telling the patient the pill is inert — has repeatedly produced improvement
relative to no treatment for self-reported symptoms.

- Kaptchuk et al. (2010) randomised 80 IBS patients to open-label placebo or no treatment
  and found higher global improvement scores with the honest placebo. Single trial,
  unblinded by design. **Grade B.**
- Charlesworth et al. (2017) meta-analysed 5 trials (n≈260) of placebos without deception
  versus no treatment across IBS, depression, allergic rhinitis and back pain; pooled
  standardised effects were moderate and significant for self-reported outcomes.
  **Grade A for "self-reported symptoms improve"; the limitations are small n and few
  trials.**
- von Wernsdorff et al. (2021) meta-analysed open-label placebo across clinical trials and
  again found benefits, concentrated in patient-reported outcomes. **Grade A**, with the
  caveat that heterogeneity is substantial and blinding is impossible by construction.

- Kaptchuk & Miller (2015) argue, in a brief NEJM perspective, that placebo effects are
  clinically legitimate rather than obstacles to be designed away. **Grade C** (expert
  perspective, not primary data) for that argument; **A** for the underlying claim that the
  effects exist.

**Contested.** Hróbjartsson & Gøtzsche's Cochrane review (2010) of 202 trials found no
significant pooled effect of placebo on binary or continuous outcomes overall, with possible
effects only on patient-reported outcomes such as pain, and cautioned that much apparent
effect is reporting bias, regression to the mean and natural history. This is the central
unresolved tension in the field and it is not settled. **Grade A for the negative framing.**

**Bearing on the sandbox.** Weak and indirect. The sandbox models a *quantitative
multiplier on a repair rate*, not a patient-reported symptom score. The placebo literature
supports "expectation can change how people report and experience symptoms". It does **not**
support "expectation multiplies tissue repair by a factor". Anyone porting the placebo
literature into this sandbox should treat that port as an **unvalidated analogy (Grade D)**.

## 2. Expectancy and conditioning

**Reasonably well supported.** Placebo analgesia is partly expectancy-driven and partly
conditioning-driven, and these can be dissociated pharmacologically.

- Amanzio & Benedetti (1999) showed in human experimental pain that expectation-activated
  placebo analgesia was reversible by naloxone whereas conditioning-activated analgesia was
  not, implying partially separable mechanisms. **Grade C** (mechanistic human; small
  samples, experimental pain rather than clinical outcome).
- Colloca & Benedetti (2005) review the neurobiology: opioid, cholecystokinin and dopamine
  involvement, learning effects, and the nocebo counterpart. **Grade C** (narrative/
  mechanistic review).
- Colloca & Barsky (2020) frame placebo and nocebo explicitly as effects of expectation on
  health, with legitimate clinical relevance. **Grade C** for mechanism, **A** for the
  claim that expectancy effects are real and pervasive.
- Wager & Atlas (2015) provide the most widely cited synthesis of placebo mechanisms,
  connecting context and learning to health outcomes, and are explicit that effect sizes
  depend heavily on the outcome measured. **Grade C** for mechanism, and their caveat about
  outcome-dependence is the reason this project does not transfer those effect sizes to
  wound repair.

**Contested.** Effect sizes are unstable, hard to replicate across settings, and strongly
dependent on the ritual and the relationship. Conditioned placebo responses can invert or
extinguish. Dosing, timing and context effects are poorly characterised.

**Bearing on the sandbox.** Direct but only structural. Expectancy is defensible as a
*module* — the project already names its `expectancy` module as configurable, representing
placebo/nocebo-style effects. What is not defensible is asserting a magnitude. Any default
parameter for that module must be labelled a **placeholder (Grade D)**.

## 3. Psychoneuroimmunology

**Reasonably well supported (mechanism).** Communication between the nervous and immune
systems is real and well characterised.

- Tracey (2002) described the inflammatory reflex: vagus-mediated sensing of inflammation
  with cholinergic anti-inflammatory output. **Grade C** for mechanism in animals/humans;
  this is a pathway, not a therapy.
- Dantzer et al. (2008) review cytokine-to-brain signalling producing sickness behaviour and
  the inflammation–depression hypothesis. **Grade C** for mechanism, **D** for any strong
  causal claim about depression.

**Contested.** The size, direction and clinical exploitability of these pathways in humans
remain debated. Immune-to-brain signalling is easy to demonstrate and hard to convert into
predictable clinical benefit. Bioelectronic/anti-inflammatory stimulation results have not
been as clean as the mechanism literature implies.

**Bearing on the sandbox.** The sandbox's **mediator field** (ATP, cytokines, growth
factors, perfusion, neural drive) is a legitimate *naming* of variables that exist. That is
where the legitimacy stops: the sandbox treats those variables as a deterministic
intermediate layer whose coefficients are invented. **Grade D for the field's dynamics**;
**Grade C only for the existence of neural–immune signalling as a concept.**

## 4. Psychological stress and wound-healing delay

This is the most directly relevant theme, and it is the one the sandbox's marketing must not
misread.

**Reasonably well supported.** Psychological stress is associated with slower healing in
standardised human wound models.

- Kiecolt-Glaser et al. (1995) found slower healing of standardised punch-biopsy wounds in
  women caring for relatives with dementia versus matched controls, with immune correlates.
  **Grade C** (observational, small, heavily confounded by age, health and caregiving load).
- Broadbent et al. (2003) found higher pre-operative stress predicted slower early repair of
  surgical wounds. **Grade C** (observational, small).
- Walburn et al. (2009) systematic review and meta-analysis of 22 studies found a reliable
  association between stress and delayed healing, with effects on both self-report and
  biological measures. **Grade B**: a meta-analysis, but of studies that are small,
  heterogeneous, rarely blinded and mostly observational.
- Gouin & Kiecolt-Glaser (2011) and Koschwanez & Broadbent (2011) review the methods and
  mechanisms, including the hard problem of measuring healing in humans.
  **Grade C / methods review.**
- Robinson et al. (2017) reviewed 19 trials of psychological interventions and found
  evidence suggesting *improved* healing, strongest for surgical wounds. **Grade B** as a
  systematic review of trials, but the trials are small, heterogeneous, rarely blinded and
  the review mixes outcome types.

**Contested.** Whether stress *causes* delay or merely correlates with it is not
established — the confounders (sleep, smoking, medication, comorbidity, distress about the
wound itself) are severe. The direction of the intervention literature is positive but
fragile, and effects on self-report are much better established than effects on measured
tissue repair.

**Bearing on the sandbox.** This is a **partial, one-directional analogy**, and it is the
strongest argument the project can honestly make:

- There is real evidence that a *psychological state* correlates with *healing rate*.
- That is **not** evidence that attention multiplies healing. Stress reduction removes a
  plausible brake; the sandbox adds an accelerator. **Removing a brake is not the same as
  adding a gain term.**
- The sandbox models the accelerator, and it does so with invented coefficients.
  **Grade D for the sandbox's mechanism; Grade B for the background claim that stress and
  healing are associated.**

## 5. Interoception and attention to bodily signals

**Reasonably well supported.** Interoception — sensing internal bodily state — is a
measurable construct, and attention to bodily signals changes experience.

- Craig (2009) proposes anterior insula as a substrate for interoceptive awareness and
  subjective feeling. **Grade C/D**: influential, largely mechanistic and inferential.
- Garfinkel et al. (2015) distinguish interoceptive **accuracy** (objective heartbeat
  tracking), **sensibility** (self-reported) and **awareness** (metacognitive), showing they
  are dissociable. **Grade C** (psychometric validation in healthy participants).
- Farb et al. (2015) review interoception, contemplative practice and health, proposing that
  training attention to bodily signals can influence health-related processes.
  **Grade C** for the phenomenological and psychometric findings, **D** for downstream
  health-outcome claims.
- Villemure & Bushnell (2002) review how attention and emotion modulate pain processing.
  **Grade C**: attention demonstrably changes pain experience and its neural correlates.

**Contested.** Whether improved interoceptive accuracy is beneficial is contested — it is
variably associated with better and worse outcomes, and it is not a straightforward
therapeutic target. The literature linking interoceptive training to *physical* healing is
essentially absent.

**Bearing on the sandbox.** The sandbox's "conscious system attending to a tissue" is a
recognisable framing for interoceptive attention (Grade C as a *concept*). There is no
evidence that attending to a wound changes its repair rate. **Grade D for the sandbox's
mechanism.**

## 6. HRV and breathing biofeedback

**Reasonably well supported for self-reported stress and anxiety.**

- Goessl et al. (2017) meta-analysed 14 studies of HRV biofeedback and found moderate
  effects on self-reported stress and anxiety. **Grade B/A**: a meta-analysis, but of small
  studies with often-waitlist controls and no blinding. Leaning **B**.
- Lehrer & Gevirtz (2014) explain why resonant-frequency breathing raises HRV amplitude via
  baroreflex gain. **Grade C** (mechanistic review).
- Zaccaro et al. (2018) systematically review slow-breathing studies and report effects on
  autonomic, emotional and cognitive measures. **Grade B**, with the caveat that protocols
  and outcome measures are highly heterogeneous.

**Contested.** Blinding is essentially impossible in breathing interventions, expectancy and
relaxation are not separable from the technique, and effects on hard physiological endpoints
are much less consistent than effects on anxiety questionnaires.

**Bearing on the sandbox.** This is the most *implementable* adjacent literature: HRV
biofeedback is exactly the kind of thing the project's optional hardware adapters
(heart-rate over BLE, LSL streams, serial bridge) could carry. It supports a claim about
**anxiety and autonomic measures**, not about healing. **Grade B for the biofeedback claim
as scoped; Grade D if used to license any tissue-repair claim.**

## 7. Nocebo effects

**Reasonably well supported.** Negative expectation produces real symptoms: pain,
nausea, and in some trials adverse-event reporting patterns that track the informed-consent
wording rather than the pharmacology.

- Colloca & Miller (2011) review nocebo mechanisms (expectation, conditioning, learning) and
  the clinical and ethical implications of disclosure. **Grade C** for mechanism; the
  behavioural phenomenon itself sits at **A/B**.
- Colloca & Barsky (2020) cover placebo and nocebo together. **Grade A** for existence and
  clinical relevance, **C** for mechanisms.

**Contested.** Nocebo is hard to study without deceiving participants, so the literature is
ethically constrained. Attribution of adverse events to expectation versus underlying
disease is frequently ambiguous.

**Bearing on the sandbox.** Directly relevant to the design of the `expectancy` module: if
expectancy effects are real in *both* directions, a model of attention as pure benefit is
missing the negative branch. **This is a design critique (Grade C), not a healing claim.**

## 8. Mindfulness and immune measures

**Weak, preliminary.**

- Black & Slavich (2016) systematically review RCTs of mindfulness meditation on immune
  markers. Findings are mixed: some inflammatory markers move in some studies, others do
  not, samples are small and outcome measures are heterogeneous. The authors themselves call
  the results preliminary. **Grade C/D**, and it does not establish any wound-healing effect.

**Bearing on the sandbox.** Included to be explicit that the "attention is good for the
immune system" shortcut does not survive contact with the primary literature at the
resolution the sandbox would need. **Grade D for any tissue-level inference.**

## Summary table

| Theme | Best grade for the well-supported claim | Grade for the sandbox's actual assumption |
| --- | --- | --- |
| Placebo / open-label placebo | A (self-reported symptoms) | D |
| Expectancy and conditioning | A (existence) / C (mechanism) | D (no magnitude is supported) |
| Psychoneuroimmunology | C (mechanism) | D |
| Stress and healing delay | B (association) | D (accelerator is unmodelled by this evidence) |
| Interoception and attention | C | D |
| HRV / breathing biofeedback | B (stress and anxiety) | D (no tissue outcome) |
| Nocebo | A (existence) | D |
| Mindfulness and immune markers | C/D (preliminary) | D |

**Bottom line:** the adjacent literature is real, interesting and worth reading. None of it
establishes the sandbox's core assumption. The honest description remains: *the model makes
an assumption explicit and lets you explore its consequences.*
