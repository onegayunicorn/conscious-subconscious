# Messaging

Message hierarchy for conscious-subconscious v0.1.0. Everything below is subordinate to the
boundary rule: this is an educational and artistic modelling sandbox, not a medical device,
not clinical evidence, not medical advice.

## 1. One-liner

> An open-source sandbox that takes one unvalidated assumption — that deliberate attention
> multiplies a tissue repair rate — and lets you explore its consequences reproducibly.

Shorter variant for tight spaces:

> A reproducible sandbox for exploring an assumption about attention and repair, not for
> proving it.

## 2. Elevator pitch (four sentences)

> conscious-subconscious models two processes on a damaged tissue model: an autonomous
> **subconscious** homeostatic repair loop, and a deliberate **conscious** attention loop that
> spends a finite **attention budget** through a configurable **expectancy module**. It is
> deterministic and seeded, with a virtual clock, so every run is reproducible; the core is a
> Python 3.12 package with a FastAPI service layer, a JSON-Schema protocol envelope and a
> TypeScript/React console, plus optional hardware adapters (LSL, BLE heart rate, serial).
> The assumption at the centre of it came from an AI-generated design document whose numbers
> are invented, and the repository says so in the same file it uses them in. It is MIT, it is
> educational and artistic, and it is not a medical device or clinical evidence.

## 3. Three proof points

1. **Reproducibility as the load-bearing feature.** Seeded RNG plus a virtual clock means
   anyone gets the same numbers you did. That is what makes it a teaching artefact rather
   than an animation. Claim: *you can reproduce any run in the README, byte for byte.*
2. **The assumption is labelled, not hidden.** Every claim in the source material is graded
   A–D in `research/evidence-grading.md`, and the specific numbers from the source PDF
   (`healing_rate = 0.5`, a random 1.0–3.0 "conscious boost") are graded **D** — invented,
   with no measurement behind them. Claim: *you can audit the assumption instead of taking it
   on faith.*
3. **A real engineering stack, not a notebook.** Python core, FastAPI service, JSON-Schema
   envelope, React console, adapter boundary for LSL/BLE/serial, Docker and Kubernetes.
   Claim: *it is small enough to read in an afternoon and structured enough to extend for a
   term project.*

Measurability note: proof points 1 and 3 are verifiable by running the code. Proof point 2 is
verifiable by reading the repository. None of them is a claim about biology — and none of
them needs to be.

## 4. Objection handling

| Objection | Honest answer |
| --- | --- |
| "Isn't this pseudoscience?" | The repository encodes the assumption explicitly and labels it **unvalidated**. What it grades as established is the adjacent literature (stress and healing delay, placebo for self-reported symptoms, HRV biofeedback for anxiety) — and none of those establishes the model's mechanism. It also grades the source document's own numbers as **D: invented**. A project that publishes its own weak grades is doing the opposite of pseudoscience. |
| "So does focusing on a wound heal it faster?" | Unknown, and this project does not claim it. The human evidence is about *stress impairing* healing, which is a different direction of effect, and it is mostly about self-reported outcomes. There is no well-powered, well-blinded trial showing that attention speeds wound closure. |
| "Then what's the point?" | The model makes an assumption explicit and lets you explore its consequences. That is useful for teaching, for criticising the assumption, and for showing exactly where a real study would have to start. |
| "Is this a medical device / can I use it for health decisions?" | No, and no. It is not a medical device, not clinical evidence, and not medical advice. It does not diagnose, treat, cure or prevent anything. |
| "Are the numbers calibrated?" | No. `healing_rate = 0.5` and a 1.0–3.0 random boost have no unit, no measurement and no provenance. They are placeholders, and the repository labels them as such. |
| "Can I buy it / is there a Pro tier?" | Payments are not implemented in this project — no pricing, no tiers, no checkout, no subscriptions. It is MIT-licensed source on GitHub. |
| "Does it use my health data?" | There is no cloud service and no accounts. Optional hardware input (heart rate over BLE, LSL streams, serial) is an input channel; it is documented as a data path, not as evidence, and nothing is uploaded anywhere. |
| "Is the Python package production-ready?" | It is v0.1.0 and honest about it. It is a sandbox: small, readable, deterministic, and explicitly not validated. |
| "Why should I trust your bibliography?" | Every reference in `research/bibliography.bib` was checked against Crossref and/or PubMed for authors, year, venue, volume/pages and DOI or PMID. Anything that could not be verified was omitted rather than guessed. |

## 5. Message testing notes (what to lead with)

- Lead with **reproducibility + labelled assumption**. Lead with the honesty and the
  engineering; the biology is the *subject*, not the *result*.
- Never lead with the tissue. Anything that makes tissue the hero invites a health claim.
- For educators, lead with the grading table. For developers, lead with the protocol envelope
  and adapter boundary. For hobbyists, lead with the fact that their data is an input, not a
  proof.

## 6. Do-not-say list

Do not write, imply, or let a graphic suggest any of the following:

1. **"Visualisation heals tissue faster."** The exact claim this project exists to avoid.
2. "Attention/focus/consciousness speeds up or improves healing."
3. "The simulation shows that the mind can heal the body."
4. "Static energy from the brain", "directing energy", "clearing blocked energy", or any
   other phrase from the source document presented as mechanism.
5. "Clinically validated", "evidence-based", "clinical-grade", "FDA/CE/MHRA-cleared",
   "medically proven", or any regulatory implication.
6. "Treats / cures / prevents / diagnoses" anything, in any organism.
7. "Recommended for" any patient group, condition, recovery, or surgery.
8. "The numbers come from research" or "the model is calibrated to human data".
9. "Proven to work", "science says", "studies confirm" — with or without a citation to back
   it, unless the specific claim is the adjacent-literature claim above and it is graded.
10. Any pricing, tier, checkout, subscription, or paid-plan language: payments are not
    implemented.
11. "Powered by AI", "AI-driven healing", or any framing that positions an AI-generated
    document as a source of medical insight. The AI-generated provenance is a *limitation*
    to disclose, not a feature to market.
12. Testimonials, endorsements, or before/after imagery of any wound, person, or animal.

## 7. Required disclaimers (copy verbatim)

Short form, for footers and cards:

> Educational and artistic simulation only. Not a medical device, not clinical evidence, not
> medical advice. No claim that attention heals tissue.

Long form, for README-scale text:

> conscious-subconscious is an educational and artistic modelling sandbox. It is not a
> medical device, it is not clinical evidence, and it is not medical advice. Nothing here
> diagnoses, treats, cures or prevents anything, and nothing here should inform a health
> decision. The mechanism it models — that conscious attention multiplies a repair rate — is
> an unvalidated assumption carried over from an AI-generated design document whose numerical
> parameters are invented. The sandbox makes that assumption explicit and lets you explore
> its consequences; it does not demonstrate that the assumption is true.
