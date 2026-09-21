# Personas

Four concrete audiences. Each has goals, likely objections, and what would actually convince
them. Objections are written the way the person would say them, including the hostile ones —
the hostile objections are the useful ones.

**Boundary reminder:** none of what follows addresses a medical audience. This project has no
clinical use, no clinical claim, and is not a medical device.

## P1 — Ravi, cognitive-science MSc student

- **Context.** Taking a module on attention and consciousness. Has read the placebo and
  interoception literature at a survey level. Needs something concrete for a seminar
  presentation and a small coursework project.
- **Goals.** A runnable artefact that lets them change one thing and see what happens; a
  citation-ready summary of what is and is not established; something they can fork in an
  afternoon.
- **Objections.**
  - "Isn't this just a toy with made-up numbers?"
  - "Will my supervisor think I'm citing pseudoscience?"
  - "Why Python *and* TypeScript? I only have time for one."
- **What convinces them.** The `research/` tree: a rubric, graded claims in a table, and a
  bibliography where every entry has a DOI. The sentence "the model makes one assumption
  explicit and lets you explore its consequences" is quotable in a slide. Seed + virtual
  clock means their lecturer can reproduce the exact figure.
- **What loses them.** Any hint that the model is calibrated, or that the project thinks it
  has found something about healing.

## P2 — Ines, simulation / interactive-media developer

- **Context.** Builds browser-based simulations and installations. Comfortable with
  TypeScript/React, vaguely comfortable with Python. Previously worked on a "biofeedback"
  installation and got uncomfortable about what it was implying.
- **Goals.** A clean architecture to extend: a documented protocol envelope, a real service
  layer, a console they can restyle, a plausible path to hardware (an HR strap over BLE).
  Wants the ethics framing to be *pre-solved* so they do not have to invent it in a gallery.
- **Objections.**
  - "Is the protocol spec actually documented, or is it three JSON blobs in a folder?"
  - "Will I have to rewrite the renderer to change the visuals?"
  - "Assumption-labelling sounds like it will make the installation boring."
- **What convinces them.** The JSON-Schema envelope and adapter boundary documented well
  enough to write a new adapter against; the SVG key visual and palette showing that honest
  framing does not require ugly output; the `media/` assets being directly usable.
- **What loses them.** Undocumented coupling between the core package and the console, or a
  licensing surprise. The MIT licence is the answer, stated plainly.

## P3 — Dr. Osei, science educator / communicator

- **Context.** Teaches science communication or runs undergraduate labs. Wants an example of
  *how to be honest about a model* that students can internalise.
- **Goals.** A single artefact that shows an assumption being labelled, graded, cited and
  bounded — the whole loop, not a slogans version. Wants to teach the difference between
  "the simulation shows" and "the simulation assumes".
- **Objections.**
  - "Will students just see the pretty curve and stop reading?"
  - "Is the boundary statement buried, or is it in every file?"
  - "Can I use it in a slide deck without a licensing conversation?"
- **What convinces them.** The boundary statement at the top of every file in all three
  trees; the social card that carries the disclaimer in small type by design; the grade-D
  table that names the source PDF's numbers as invented.
- **What loses them.** Any resource that reads as marketing first. Educators are the audience
  most allergic to overclaiming, and the easiest to lose with one loose sentence.

## P4 — Marcus, biofeedback / HRV hobbyist

- **Context.** Runs an HRV setup at home, has read about slow breathing, has strong opinions
  about wrist-sensor accuracy. Skeptical of wellness claims, slightly hurt that his hobby is
  associated with them.
- **Goals.** Somewhere to plug real heart-rate data in that does not pretend the data proves
  anything; a sandbox where he can log a session and see what the model does with it; a
  project that treats "protocol boundary" as an engineering problem rather than a slogan.
- **Objections.**
  - "Is this going to tell me my consciousness is healing me?"
  - "Does the BLE adapter actually exist, or is it a stub with a README?"
  - "Why would I use this instead of plotting my own CSVs?"
- **What convinces them.** The clear statement that hardware input is an *input* and not
  evidence; the honest citation of HRV meta-analyses with their limitations (Goessl et al.,
  2017 grades B in this project, not A); the mediator field being visibly a model rather
  than a measurement.
- **What loses them.** One sentence that sounds like a wellness claim, or a "integration"
  that turns out to be a TODO.

## Cross-persona notes

- **The boundary statement is the pitch, not the fine print.** All four personas react
  positively to it and negatively to its absence. Keep it near the top.
- **Nobody is convinced by the simulation; they are convinced by the honesty apparatus.**
  The differentiators are the grading rubric, the verified bibliography and the reproducible
  runs.
- **Nobody in these personas is a patient or a clinician.** Do not address clinical
  audiences, and do not build personas that require a clinical claim to be interesting.
