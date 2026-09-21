# FAQ

Including the question the project has to answer first.

> **Boundary.** Nothing on this page is medical advice, and nothing on it
> supersedes [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## "Isn't this pseudoscience?"

Mostly the honest answer is: **the model is not the pseudoscience; the *claims
about* it would be.**

Here is the difference, stated as concretely as possible.

A pseudoscientific artefact hides a magical mechanism behind plausible-looking
numbers. This project does the opposite:

1. **The assumption is a named number.** The entire "mind over tissue" claim is
   `conscious.neural_drive_coupling` in
   `src/conscious_subconscious/parameters.py`, with the grade `invented` and a note
   reading: *"THE CENTRAL UNVALIDATED ASSUMPTION... Set this to 0.0 to switch the
   entire mind-over-tissue claim off."* It is not distributed across a hundred
   places. It is one key.
2. **The assumption is graded `invented`.** Its own docstring says it "has no
   empirical basis" because it came from the source design document's random
   `1.0–3.0` boost. Every run prints the grade of that parameter before it prints
   any result.
3. **A control scenario ships where the assumption is zero.** `focused-uncoupled`
   sets the coupling to `0.0` while still holding attention, and CI asserts that
   every *repair* metric then matches `baseline` exactly. If attention leaked into
   repair by any other route, that assertion would fail. The control is not a
   footnote; it is a test. (Attention *accounting* — focus hours, attention spent,
   fatigue episodes — does differ, because the control really does hold attention.
   The assertion is scoped to the repair path for exactly that reason.)
4. **A sweep shows the conclusion depends on the invented constant.**
   `cs-sim sweep --param conscious.neural_drive_coupling --values 0:2:0.5` reports
   time-to-50%-repair falling from 33.95 h to 20.05 h purely as a function of that
   knob. The project prints that table and calls it a consequence of the choice.
5. **The adjacent literature is reviewed and honestly graded.**
   `research/literature-review.md` grades placebo/expectancy effects as A for
   self-reported symptoms, stress-and-healing as B for association, HRV
   biofeedback as B for *stress and anxiety* — and grades the project's own
   assumption **D** in every row, because no adjacent evidence supports an
   accelerator on tissue repair.
6. **Payments, accounts and clinical functions are absent.** Not "coming soon" —
   absent. There is nothing to sell and nothing to enrol in.

So the project's relationship to pseudoscience is: it is a simulation of an
unvalidated assumption, shipped with the receipt for why it is unvalidated. The
pseudoscientific failure mode is not "modelling something speculative"; it is
*claiming the model settled it*. That claim is the one this repository refuses to
make, which is why the refusal appears in the disclaimer, in the CLI epilog, in the
report footer and at the top of every document.

Where the criticism does land, and fairly:

- **Building it at all can be misread.** A simulated number is quotable out of
  context. The mitigation is the disclaimer travelling with every output, and it is
  imperfect.
- **The `invented` values look like data.** They are formatted to three decimals
  and they come out of a deterministic run; that makes them *look* measured. The
  grade column is the only thing that distinguishes them, and most readers skip
  tables.
- **"Educational and artistic" is doing real work.** If you are looking for a
  research-grade model, this is the wrong repository, and no amount of clean code
  fixes that.

## Does this show that focusing on a wound heals it faster?

**No.** It shows what happens *inside this model* when you instruct it to assume
that. The library of real evidence around the claim — stress and healing delay,
placebo for subjective outcomes, HRV biofeedback for anxiety — is reviewed in
`research/literature-review.md`, and none of it establishes an effect of attention
on tissue repair.

The one adjacent finding that is genuinely strong (stress correlates with slower
healing) is the *mirror image* of the model's claim. Removing a brake is not the
same as adding an accelerator, and the sandbox models an accelerator.

## Can I use it to predict how long my injury will take to heal?

**No.** There is no patient, no population, no measurement and no clinical
endpoint in the model. `time_to_50pct_repair_hours` is the first time a scalar
variable crosses a threshold derived from a normalised starting value. It is not a
prediction about a body, and using it as one is exactly the misuse the disclaimer
prohibits.

## Is it a medical device?

**No.** It has no clinical function, no regulatory clearance and no clinical
claim. Nothing in `deploy/` changes that: a Kubernetes manifest around a simulation
is still a simulation.

## Does it do biofeedback?

The hardware adapters **read** from sensors and the autonomic module can accept
an HRV-style index. Nothing in the project sends anything to a person: there is no
stimulation, actuation or write method in any adapter, and `bidirectional` defaults
to `False`. That boundary is deliberate and is treated as a safety property in
`security/threat-model.md`.

If you want HRV biofeedback, the evidence for stress and anxiety outcomes is real
(grade B in the review) and this project is not the tool for it.

## Why not just use numpy?

Because the engine should run anywhere, including a locked-down or offline
interpreter, and because "reproducible" is easier to defend with no dependency
graph at all. The core package declares **zero** runtime dependencies. `numpy` and
`matplotlib` live in the optional `science` extra, `fastapi`/`uvicorn`/`pydantic`
in `api`, the device drivers in `devices`.

## Why is the model so small? There's no geometry, no cells, no scar.

Correct, and it is stated in `docs/model-spec.md` rather than left for you to
notice. The scalar tissue is inherited from the source design document, so keeping
it makes the port honest. Adding geometry would add parameters — and every new
parameter would be another `assumed` number, making the model *look* more
scientific without being better supported. That trade is documented in
`research/open-questions.md`.

## Can I trust the numbers to be reproducible?

Yes, and you can check it rather than trust it. Runs use a virtual clock and named
SHA-256-derived random substreams, so the same seed and configuration produce
identical output byte for byte. Every result carries a `run_digest`; CI runs
`cs-sim compare` twice and diffs the output, and asserts the
`focused-uncoupled` control still equals `baseline`. The one source of
non-determinism, `conscious.neural_drive_jitter`, is `0.0` by default.

## Is there a pricing tier? A hosted version? An account?

**No.** Payments, subscriptions, checkout and payment integrations are not
implemented anywhere in this repository, and this documentation describes nothing
of the kind as existing. There is no hosted instance, no user database and no data
collection by the project.

## Where do I report a security problem?

See [`SECURITY.md`](https://github.com/onegayunicorn/conscious-subconscious/blob/main/SECURITY.md).
Private reporting goes through GitHub's private vulnerability reporting on the
repository. There is no dedicated security email address configured for this
project yet, and `SECURITY.md` says so rather than inventing one.

## Something in the docs disagrees with the code. Which is right?

The code. Documentation is a derived artefact and drifts; `docs/model-spec.md` is
transcribed from `src/conscious_subconscious/model/` and `parameters.py`, which are
the source of truth. A documentation bug is worth an issue — the
[bug report template](https://github.com/onegayunicorn/conscious-subconscious/issues/new/choose)
has an area for exactly this.
