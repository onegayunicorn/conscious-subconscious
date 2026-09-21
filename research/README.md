# research/ — evidence, grading and open questions

This tree holds the epistemic backbone of **conscious-subconscious** (v0.1.0,
<https://github.com/onegayunicorn/conscious-subconscious>, MIT).

The project is a **reproducible simulation sandbox**. It models the interaction between an
autonomous "subconscious" homeostatic repair process and a deliberate "conscious"
attentional process applied to a damaged tissue model. Nothing here is a product, a therapy,
or a result about human biology.

## Boundary statement (applies to every file in this tree)

- conscious-subconscious is an **educational and artistic modelling sandbox**. It is **not a
  medical device**, **not clinical evidence**, and **not medical advice**.
- No claim is made that this software, or the behaviour it simulates, **diagnoses, treats,
  cures, prevents, or speeds the healing of** anything in any organism.
- The core mechanism modelled — that *conscious attention multiplies a repair rate* — is an
  **unvalidated assumption**, carried over from an AI-generated design document. The sandbox
  makes that assumption explicit and lets you explore its consequences. It does not
  demonstrate that the assumption is true.
- The sandbox cannot establish causation about human healing, and no output of it should be
  read as evidence about humans.

## What is in this tree

| File | Purpose |
| --- | --- |
| `README.md` | This file: scope, boundary, how the tree is maintained |
| `evidence-grading.md` | The A–D rubric, plus a blunt grade for each specific claim in the source PDF |
| `literature-review.md` | Review of the genuinely adjacent published literature, graded claim by claim |
| `open-questions.md` | Falsifiable questions the sandbox can explore, and what data human testing would need |
| `experimental-design.md` | A design sketch (not a protocol, never run) for studying attention-modulated healing |
| `bibliography.bib` | BibTeX for exactly the references cited in this tree |

## Evidence-grading rules

1. **Every citation must be real and verified.** Each entry was checked against Crossref
   and/or PubMed before inclusion; author list, year, venue, volume/pages and DOI or PMID
   were recorded from that check. If a reference could not be verified, it was omitted —
   omitting a reference is acceptable, inventing one is not.
2. **Every claim carries a grade** from `evidence-grading.md` (A/B/C/D). No claim appears
   without one.
3. **No grade inflation.** A well-conducted meta-analysis of small, heterogeneous,
   non-blinded trials is not automatically an A. Where the grading is arguable, the
   disagreement is stated in the text rather than smoothed over.
4. **Mechanism ≠ treatment.** A demonstrated physiological pathway (e.g. a neural-immune
   reflex) does not license a claim that a psychological intervention changes a clinical
   outcome. These are graded separately.
5. **The PDF's numbers are treated as invented until shown otherwise.** No unverified
   numeric parameter from the source document is presented as a finding.

## Known limits of this tree

- The review is not a systematic review: no PRISMA search strategy, no dual screening, no
  risk-of-bias tooling. It is a curated narrative review by the project authors.
- Most references are reviews and mechanistic papers, not primary RCTs about tissue repair,
  because that literature is thin and mostly about self-reported outcomes.
- The grade letters are a communication device, not a validated instrument.

## Support and sponsorship

Not implemented. This project has **no payment system**: no pricing, no tiers, no checkout,
no subscriptions. If a support mechanism is ever added it will be a plain link to the
repository's own channels and will not gate any content in this tree.
