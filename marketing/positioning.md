# Positioning

**Boundary:** conscious-subconscious is an educational and artistic modelling sandbox. It is
not a medical device, not clinical evidence and not medical advice, and it makes no claim
about healing in any organism. Its core mechanism — that conscious attention multiplies a
repair rate — is an explicitly labelled, unvalidated assumption.

## The honest one-liner

> **conscious-subconscious is an open-source sandbox that takes one unvalidated assumption —
> that deliberate attention multiplies a tissue repair rate — and lets you explore its
> consequences reproducibly, instead of arguing about them.**

## What this project is

- A **reproducible simulation sandbox** (v0.1.0, MIT, `onegayunicorn/conscious-subconscious`)
  modelling two interacting control processes on a damaged tissue model: an autonomous
  **Subconscious system** (homeostasis, no attention cost) and a deliberate **Conscious
  system** (finite **attention budget**, configurable **expectancy module**).
- A **worked example of intellectual honesty in modelling**: the parameters are invented, and
  the repository says so, in the same paragraph as it uses them.
- A **teaching artefact**: seeded RNG and a virtual clock make every run reproducible, so the
  same numbers come out for everyone, which is what makes it usable in a classroom.
- An **engineering demo**: a Python 3.12 core package, a FastAPI service layer, a
  JSON-Schema protocol envelope, a TypeScript/React console, and optional hardware adapters
  (LSL, BLE heart rate, serial bridge) with Docker/Kubernetes deployment.
- A **conversation starter** about where simulation stops and evidence starts.

## What this project is not

| Not this | Why not |
| --- | --- |
| A medical device | It has no clinical function, no regulatory clearance, and no clinical claim. |
| Clinical evidence | It produces numbers from equations, not from participants. |
| Medical advice | Nothing here should inform anyone's health decisions. |
| A healing app | There is no evidence that attention to a wound changes its repair rate; the model assumes it. |
| A "quantified self" product | No accounts, no data collection, no payments, no cloud sync of any kind. |
| A paid product or subscription | Payments are not implemented in this project. |
| A proof of anything | A simulation contains the assumptions written into it. |

## Who it is for

1. **Simulation and interactive-media developers** who want a small, honest, well-structured
   model with a real service layer and a real UI to extend.
2. **Cognitive-science and HCI students/lecturers** who want a concrete artefact for
   discussing attention, homeostasis, expectancy and the limits of models.
3. **Science communicators and educators** who need an example of explicit assumption-labelling.
4. **Biofeedback/HRV hobbyists** who already run heart-rate devices and want a sandbox that
   treats the protocol boundary honestly.

## Competitive and adjacent space

| Adjacent category | Examples of the category | How this project differs |
| --- | --- | --- |
| Reproducible simulation sandboxes | NetLogo models, Mesa (Python agent-based modelling), agent-based educational models | Those are general-purpose. This is one specific, opinionated two-process model with a service layer and a console, and an unusual emphasis on stating its own evidentiary grade. |
| Cognitive-architecture projects | ACT-R, Soar, LIDA-style architectures | Those aim at general cognition with decades of validation. This is a narrow toy model of two interacting control loops, and does not claim to be a cognitive architecture. |
| Biofeedback toys and apps | Consumer HRV/breathing apps, open-source HRV dashboards | Those have a measurable target (heart rate, breathing). This project's target is a *simulated* tissue variable, which is exactly why it must not be sold like a biofeedback product. |
| "Mind-body healing" content | Wellness media, visualisation apps | That category makes health claims. This project refuses to, by design. The distance from that category is the point. |

**Positioning statement for the space:** other projects either simulate general systems
without an evidentiary stance, or make health claims without verification. This one simulates
a narrow system and grades its own assumptions in public.

## Anti-positioning (what to never imply)

- That visualising, focusing on, or thinking about a wound speeds its healing.
- That this repository is a step toward a treatment, a therapy, a diagnostic, or a device.
- That the numbers in the simulation are calibrated to anything.
- That the project has clinical partners, data, trials, or regulatory intent. It has none.

## Support and sponsorship

**Not implemented.** There are no payment features in this project: no pricing, no tiers, no
checkout, no subscriptions. Any future support mechanism would be a plain, non-gating link to
the repository's own channels, and would be described here only once it exists.
