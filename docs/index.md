# conscious-subconscious

> **Boundary — read this first.** conscious-subconscious is an **educational and
> artistic simulation**. It is **not a medical device**. It does not diagnose,
> treat, cure or prevent any condition, and it provides **no medical advice**.
> The model encodes an **unvalidated assumption** — that conscious attention can
> modulate a modelled tissue-repair rate. That assumption is not established
> clinical fact. Do not use any output of this project to make a decision about a
> human body. The canonical wording is
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md);
> every other document links to it rather than restating it differently.

## One-line positioning

**conscious-subconscious is an open-source sandbox that takes one unvalidated
assumption — that deliberate attention multiplies a tissue repair rate — and lets
you explore its consequences reproducibly, instead of arguing about them.**

Version 0.1.0, MIT licence, `onegayunicorn/conscious-subconscious`.

## What it is

A small, deterministic simulation of two interacting control processes acting on a
single scalar "tissue" variable:

- a **subconscious system** — autonomous homeostatic repair that runs every step
  and costs nothing;
- a **conscious system** — deliberate attention with a finite budget that drains
  as it is spent, recovers when released, and can be flagged as fatigued.

The two are connected by exactly one path: attention raises a modelled
`neural_drive` channel, and a single invented constant
(`conscious.neural_drive_coupling`) decides what, if anything, that does to the
repair rate. Set that constant to `0.0` and the whole claim switches off.

The project's actual differentiator is not the model. It is that the model states
what it does not know:

- every numeric constant carries a **provenance grade**, and 33 of the 34 default
  parameters carry no empirical support at all;
- a **control scenario** ships in which the central assumption is set to zero, and
  CI asserts that every repair metric is then identical to the baseline, so the
  attention path provably has no other route into the tissue;
- `cs-sim sensitivity` ranks the unsupported parameters by how much the headline
  result moves when each is perturbed — i.e. how much of the conclusion rests on a
  guess;
- every run emits a **digest**, so "reproducible" is checkable rather than claimed.

## Quickstart

The core package has **no third-party runtime dependencies**. It runs on a bare
Python 3.10–3.13 interpreter.

```bash
git clone https://github.com/onegayunicorn/conscious-subconscious
cd conscious-subconscious

# No install needed for a first look:
PYTHONPATH=src python3 -m conscious_subconscious.sim.cli run --scenario focused --report

# Or install it properly:
python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
.venv/bin/cs-sim compare
```

Three commands worth running first:

```bash
cs-sim parameters --unsupported   # what the model does not know
cs-sim compare                    # baseline vs continuous vs intermittent attention
cs-sim sweep --param conscious.neural_drive_coupling --values 0:2:0.5
```

That last one is the point of the project. It shows the headline result scaling
smoothly with a number that nobody measured.

## Where to go next

| If you want to… | Read |
| --- | --- |
| Understand the equations | [Model specification](model-spec.md) |
| Understand the evidence grades | [Provenance](provenance.md) |
| Understand how the pieces fit together | [Architecture](architecture.md) |
| Use the CLI | [Command line](cli.md) |
| Connect hardware | [Hardware](hardware.md) |
| Understand the wire format | [Protocol](protocol.md) |
| Run it somewhere | [Deployment](deployment.md) |
| Ask "isn't this pseudoscience?" | [FAQ](faq.md) |
| Know what changed when | [CHANGELOG](https://github.com/onegayunicorn/conscious-subconscious/blob/main/CHANGELOG.md) |

## What it is not

| Not this | Why not |
| --- | --- |
| A medical device | No clinical function, no regulatory clearance, no clinical claim. |
| Clinical evidence | Numbers come from equations, not from participants. |
| Medical advice | Nothing here should inform anyone's health decisions. |
| A healing app | There is no established evidence that attending to a wound changes its repair rate. The model assumes it and labels the assumption. |
| A paid product | Payments, pricing, subscriptions and checkout are **not implemented**. |
| A proof of anything | A simulation contains the assumptions written into it. |
| A validated model | Nothing in it has been fitted to data. See [model-spec.md](model-spec.md). |
