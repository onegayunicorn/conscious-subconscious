# Launch plan

A staged, no-budget plan. There is **no paid advertising assumption** anywhere in this
document: no ad spend, no sponsored placements, no influencer payments. Promotion is
documentation, community participation and word of mouth.

**Boundary:** launch communication must carry the standard disclaimer (see `messaging.md`
§7). Any channel that would require a health claim to perform is a channel we do not use.

## Stage 0 — Private / development (current)

**Goal:** make the repository defensible before anyone looks at it.

- [x] Core package, service layer, console, protocol envelope, deployment scaffolding.
- [x] `research/` tree complete: boundary statement, A–D rubric, graded PDF claims, review,
      open questions, design sketch, verified bibliography.
- [x] `marketing/` and `media/` trees complete: positioning, personas, messaging, channels,
      brand, logos and diagrams.
- [ ] Repository README updated to point at these trees (owner action, outside this scope).
- [ ] Repo metadata: description, topics (`simulation`, `reproducible-research`,
      `cognitive-science`, `biofeedback`, `fastapi`, `typescript`), MIT licence confirmed.
- [ ] One-command reproducibility check documented: fixed seed in, identical output out.
- [ ] A short `CONTRIBUTING` note stating the honesty rules are not negotiable.

**Exit criteria:** a sceptical reader can find a boundary statement, a grading rubric and a
verified bibliography without leaving the repository, and can reproduce a run in under ten
minutes.

## Stage 1 — Soft launch (invited)

**Goal:** survive the first ten critical readers before a public audience sees it.

- **Who to invite (5–15 people):** two cognitive-science researchers or PhD students who work
  on placebo or interoception; two developers who build simulations; one science educator;
  one person from the wellness-adjacent world who is likely to be hostile (the most useful
  reader).
- **How:** a direct, personal message with the repository link and a request for
  *disagreement*, not praise. Specifically ask: (a) which claims are still overclaimed,
  (b) which references are wrong or missing, (c) whether the boundary statement is strong
  enough.
- **Channels:** direct message (email, Mastodon/Bluesky DM, GitHub issue). No public posts.
- **Success signals:** at least three substantive criticisms, at least one of which changes
  the text; no reader believing the project claims a health effect; at least one reader
  quoting the one-liner back correctly.
- **Failure signals:** nobody engages; or someone reads it as a healing claim — which means
  the messaging failed and stage 2 must not start until it is fixed.

## Stage 2 — Public launch

**Goal:** one honest, well-prepared public moment.

- **Assets ready:** repo README, `media/social-card.svg` (1200×630) as the preview,
  `media/key-visual.svg` at the top of the README, `media/mind-tissue-diagram.svg` in the
  architecture docs, brand rules from `media/brand.md`.
- **Primary post:** one long-form post (see `channels.md`), the same text adapted per
  platform, never duplicated verbatim across platforms in the same minute.
- **Order of operations:** post the long-form piece first in one place; only then link from
  others, so there is a canonical URL to discuss.
- **What is posted:** what it is, what it is not, one screenshot/diagram, the assumption it
  encodes, the grade table, how to reproduce a run, and the disclaimer.
- **What is not posted:** any before/after imagery, any "healing" verb in the headline, any
  pricing language, any claim of clinical relevance.
- **Timing:** a weekday morning in the largest audience's timezone. Do not stack posts; one
  per day, maximum.
- **Success signals:** an issue or PR from someone outside the project; a correct, sceptical
  critique that engages with the assumption rather than the vibe; reproducible-run reports
  from strangers; sustained (not one-day) traffic visible in repo stats after a week.
- **Failure signals:** attention concentrated on "does this heal me?" questions; stars
  without issues or forks; anyone describing the project as a healing tool.

## Stage 3 — Maintenance and second wave

**Goal:** turn a launch into a resource.

- **Cadence:** one meaningful update per month, not a stream of noise. Each update: one
  change, one reason, one link.
- **Content types that fit this project:** a walk-through of the mediator field's equations
  with an explicit list of what is invented; a post on *why the boost distribution is not a
  model of attention*; a provenance note on the AI-generated source document; a post-mortem
  of what a real study would require (`research/experimental-design.md`).
- **Academic drift:** encourage citation of the *rubric* and the *boundary statement*, not of
  the model as a finding. If a paper cites this project as evidence of an effect, that is a
  defect to correct immediately and publicly.
- **Community:** keep issues open and answerable. Refuse pull requests that add health
  claims, pricing, or untraceable numbers.

## Risks and pre-agreed responses

| Risk | Response |
| --- | --- |
| The project is read as a healing claim | Correct it publicly, in the same thread, immediately; strengthen the wording in `messaging.md` and the README. |
| A headline or aggregator writes "app that heals you" | Reply with the boundary statement and the source; do not amplify the coverage. |
| Wellness accounts adopt the key visual without context | Because the disclaimer is baked into the social card and key visual, partial adoption still carries the caveat. |
| Silence | Do not escalate to paid promotion. Return to stage 1 and find better readers. |
| Pressure to add a payment/support tier | Declined: payments are not implemented in this project. |

## What success looks like after 6 months

Not stars. Success is: a lecturer using the grading rubric in a seminar; a developer forking
the protocol envelope for something unrelated; a critic quoting the boundary statement
approvingly; and zero instances of the project being described as a treatment.
