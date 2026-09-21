# Pull request

## What this changes

<!-- One or two sentences. If it changes behaviour, say which behaviour. -->

## Provenance / honesty checklist

This project's differentiator is that it says out loud what it does not know. A
pull request that quietly weakens that is a regression, even if the code is
correct.

- [ ] **New or changed parameters are tagged.** If I added a numeric parameter,
      it is declared once in `src/conscious_subconscious/parameters.py` with a
      `Provenance` grade (`measured`, `literature`, `assumed`, `invented`), a
      unit and a `minimum`/`maximum`. It is not a bare literal anywhere else.
- [ ] **I did not upgrade a provenance grade without evidence.** A value moved
      from `invented`/`assumed` to `literature` or `measured` only if there is a
      citation in `research/` or a measurement produced inside this repository.
- [ ] **If the model changed, `docs/model-spec.md` is updated** — equations,
      symbol-to-parameter-key table and the provenance table.
- [ ] **If the step order in `model/engine.py` changed, I said why.** The order
      is part of the model and is covered by tests.
- [ ] **No new medical claims.** Nothing in this change implies that attention,
      focus, visualisation or expectancy affects real tissue repair, and nothing
      describes the project as a device, a therapy, an intervention, a diagnostic
      or clinical evidence. See `DISCLAIMER.md`.
- [ ] **No claim that payments, pricing, subscriptions or checkout exist.** They
      do not exist in this project.
- [ ] **Determinism holds.** Running the same configuration twice still produces
      the same run digest, and the `focused-uncoupled` control still matches
      `baseline`.
- [ ] **Any new hardware path is read-only** with respect to the wearer. No
      adapter gained a write, stimulus or actuation method.

## Testing

- [ ] `make verify` passes locally (or the equivalent commands from
      `CONTRIBUTING.md`).
- [ ] New behaviour has a test. Golden tests were regenerated deliberately and
      the reason is stated below.
- [ ] I did not invent benchmarks, user counts or dates.

## Notes for the reviewer

<!-- Anything you are unsure about, and anything you deliberately did not do. -->
