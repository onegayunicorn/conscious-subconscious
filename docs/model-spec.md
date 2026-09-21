# Model specification

The equations the simulation actually evaluates, every symbol mapped to the
parameter key that supplies it, and an explicit statement of which of those
parameters have empirical support. If this page and the code disagree, the code
is right and this page is a bug — the equations below are transcribed from
`src/conscious_subconscious/model/`.

> **Boundary.** This is a specification of a simulation, not of biology. The
> model encodes an unvalidated assumption: that conscious attention can modulate
> a modelled tissue-repair rate. 33 of the 34 default parameters carry no
> empirical support. Nothing here is a medical device, clinical evidence or
> medical advice. See [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## 1. Status of the model

| Property | Statement |
| --- | --- |
| Validated against data | **No.** No parameter was fitted to a human or animal dataset. |
| Calibrated to a timescale | **Partly, by convention only.** Time is in hours; the source design document never stated a tick duration, so the per-hour rescaling is a choice. |
| Deterministic | **Yes.** Same seed and configuration ⇒ identical results, byte for byte, with a run digest to prove it. The single exception is `conscious.neural_drive_jitter`, which is `0.0` by default. |
| Mechanistic | **No.** It is a caricature: five scalar mediator channels, one scalar tissue variable, no geometry, no cell populations. |
| Intended use | Teaching, discussion, and as an engineering substrate. Nothing else. |

The model is a *port* of an AI-generated design document that halved a
`damage_level` variable each tick and added a random "conscious boost" of
`1.0–3.0`. That document's numbers are treated as evidence of nothing; they are
preserved as `invented` parameters rather than replaced with nicer-looking ones,
so that a reader can point at them.

## 2. State variables

| Symbol | Meaning | Code |
| --- | --- | --- |
| $I$ | Tissue integrity, a fraction of the ceiling | `Tissue.integrity` |
| $I_0$ | Initial integrity | `tissue.initial_integrity` |
| $I_{\max}$ | Integrity ceiling | `tissue.max_integrity` |
| $D$ | Remaining damage, $\in [0,1]$ | `Tissue.damage` |
| $A$ | Remaining attention budget, $\in [0,1]$ | `ConsciousSystem.attention` |
| $N$ | `neural_drive` mediator channel | `MediatorField.value("neural_drive")` |
| $G$ | `growth_factor` mediator channel | `MediatorField.value("growth_factor")` |
| $x_c$ | Any mediator channel $c$, one of `atp`, `cytokine`, `growth_factor`, `perfusion`, `neural_drive` | `MediatorField` |
| $J$ | Inflammation level, $\in [0,1]$ | `inflammation` signal |
| $P_{f}$ | Perfusion channel | `perfusion` signal / channel |
| $C$ | Circadian factor | `circadian` signal |
| $\tau$ | Modelled parasympathetic tone | `parasympathetic` signal |
| $E$ | Expectancy contribution to felt progress | `expectancy` signal |
| $t$ | Virtual time in hours | `VirtualClock.t_hours` |
| $\Delta t$ | Fixed step, `0.05` h by default | `dt_hours` |

$D$ is derived, not stored:

$$
D = \max\left(0,\ \frac{I_{\max} - I}{I_{\max}}\right)
\qquad\text{and}\qquad
\text{healed} \iff I \ge I_{\max} - 10^{-12}
$$

Two conventions matter here. A **channel** lives on `MediatorField` (a quantity
with units and decay); a **signal** lives in `StepContext.signals` and is
recomputed every step (a dimensionless value one component publishes and another
consumes). Channels persist across steps; signals do not.

## 3. Step order

Documented in `model/engine.py` and covered by tests, because changing it changes
results:

1. **Modules** publish derived signals and add channel production.
2. **Focus decision** — the policy reads current damage and attention.
3. **Conscious system** injects neural drive, spends or restores attention,
   computes perceived progress.
4. **Subconscious production** — growth factors and cytokines.
5. **Subconscious repair** — the *only* code path that changes $I$.
6. **Field decay** — every channel decays exponentially over one $\Delta t$.
7. **Recording** — sample the state, fold it into the metrics.

Order is part of the model rather than an implementation detail. Two examples: a
module that read `neural_drive` would see the *previous* step's value, because
modules run before the conscious system; and decay runs *after* production, so a
channel produced this step has not yet been discounted.

### Why the run always executes the full horizon

A run does not stop early when the tissue reaches $I_{\max}$. Area-under-damage
and time-to-threshold are only comparable across scenarios if every scenario is
sampled over the same window; an early exit would make a fast run look better
simply by being shorter.

## 4. Equations

### 4.1 Tissue

`model/tissue.py`. Integrity is a scalar with a ceiling:

$$
I \leftarrow I + \min\bigl(\text{requested},\ I_{\max} - I\bigr)
$$

Repair that exceeds the ceiling is counted in `wasted_repair`, not discarded, so
an overshooting rule cannot be reported as more efficient than it was.

### 4.2 Mediator field

`model/mediators.py`. Production is added (`field.add`), then every channel
decays exponentially:

$$
x_c(t + \Delta t) = x_c(t)\, e^{-\lambda_c \Delta t}
$$

with $\lambda_c$ = `mediator.<channel>.decay_per_hour`. Negative production is
rejected rather than absorbed, and a channel that underflows below $10^{-12}$ is
snapped to zero so a live channel cannot become a dead one by rounding.

### 4.3 Subconscious production

`model/subconscious.py::SubconsciousSystem.produce`:

$$
g = k_{gf}\,\bigl(1 + g_d D\bigr)\,C
\qquad\Longrightarrow\qquad
G \mathrel{+}= g\,\Delta t
$$

$$
c = k_{cy}\, D\,(1 + J)
\qquad\Longrightarrow\qquad
\text{cytokine} \mathrel{+}= c\,\Delta t
$$

This runs every step regardless of behaviour. When the circadian module is absent,
$C = 1$ and the term disappears.

### 4.4 Subconscious repair

`model/subconscious.py::SubconsciousSystem.step`. This is the whole of the
project's core claim, in four lines:

$$
S(G) = \frac{G}{G + K_{gf}}
$$

$$
R_{\text{base}} = k_{rep}\, S(G)\, \max\bigl(0,\ 1 - \rho J\bigr)\, C
$$

$$
R_{\text{total}} = R_{\text{base}}\,\bigl(1 + \lambda N\bigr)
$$

$$
\text{applied} = \min\bigl(R_{\text{total}}\,\Delta t,\ I_{\max} - I\bigr)
$$

$\lambda$ = `conscious.neural_drive_coupling` is the **central unvalidated
assumption**: the entire "attention modulates repair" claim, expressed as one
number that can be set to `0.0`. The built-in scenario `focused-uncoupled` does
exactly that, and its result is asserted in CI to be identical to `baseline`.

Three diagnostic signals are published from this step:

$$
\text{attributable} = R_{\text{total}} - R_{\text{base}}
$$

which is a decomposition of the model, not a measurement of anything.

### 4.5 Conscious system

`model/conscious.py::ConsciousSystem.step`. While focused:

$$
\text{gain} = \max\Bigl(0,\ k_{nd} A + u\Bigr), \qquad u \sim \mathcal{U}(0,\ j)
\ \text{(only if } j > 0\text{)}
\qquad\Longrightarrow\qquad
N \mathrel{+}= \text{gain}\,\Delta t
$$

$$
A \leftarrow A - \min\bigl(A,\ \delta \Delta t\bigr)
$$

While not focused:

$$
A \leftarrow \min\bigl(A_{\text{budget}},\ A + r \Delta t\bigr)
$$

Fatigue is entered when $A \le \theta_f$ and cleared only once $A > \theta_f$; the
focus policies additionally require $A \ge \theta_r$ before re-engaging, where
$\theta_r$ = `conscious.resume_attention` and $\theta_f$ =
`conscious.fatigue_threshold`. The gap $\theta_r - \theta_f$ is controller
hysteresis, not biology: without it a policy re-engages the instant it recovers
and flaps against the threshold, and the fatigue counter becomes a measure of the
controller rather than of anything modelled.

$u$ is drawn from the named substream `conscious.jitter` and is the **only**
source of non-determinism in the project. It is `0.0` by default.

### 4.6 Perception

Perceived progress is a separate quantity from integrity, on purpose:

$$
\Pi = \operatorname{clip}\bigl(k_p I + b + E,\ 0,\ 1\bigr)
\qquad
\text{gap} = \Pi - I
$$

The source design document printed one number and treated it as both what the
body is doing and what the mind sees. Conflating those two is how a simulation
starts to look like evidence, so both are tracked and their difference is
reported.

### 4.7 Modules

`model/modules/`. Each runs in step 1 and may only add to channels or publish
signals — a module may **not** touch $I$.

**Inflammation** (first-order relaxation toward a damage-driven target, clamped so
a large $\Delta t$ cannot overshoot):

$$
J^{\ast} = b_J + (1 - b_J)D, \qquad
\alpha = \min(1,\ s_J \Delta t), \qquad
J \leftarrow \operatorname{clip}\bigl(J + (J^{\ast} - J)\alpha,\ 0,\ 1\bigr)
$$

**Perfusion** (production proportional to the gap to a target; the field's decay
then pulls the channel *below* the target, which is what a leaky integrator does):

$$
T = b_P + v D, \qquad
\text{if } T > x_{perf}: \quad x_{perf} \mathrel{+}= (T - x_{perf})\, r_P \Delta t
$$

**Circadian**:

$$
\varphi = 2\pi\,\frac{t \bmod T_c}{T_c}, \qquad C = 1 + a_c \sin\varphi
$$

**Autonomic** (the bridge hardware feeds; one-way, read-only):

$$
\tau = \operatorname{clip}\bigl(g_{par}\, h,\ 0,\ 1\bigr), \qquad
x_{perf} \mathrel{+}= g_{perf}\,\tau\,\Delta t
$$

where $h$ is an external HRV-style index in $[0,1]$, defaulting to the module's
internal `0.5` resting assumption. HRV biofeedback has reasonable evidence for
*stress and anxiety* outcomes; it has no established effect on tissue repair, and
this module does not assert one — it moves a channel whose downstream effect is
the invented coupling $\lambda$.

**Expectancy** (both gains default to `0.0`, i.e. disabled):

$$
b_e = 1 - D, \qquad E = p_e\, b_e, \qquad
\text{if } g_e > 0: \quad N \mathrel{+}= g_e\, b_e\, \Delta t
$$

The perception gain $p_e$ shifts *felt* progress only and has no physical effect.
The physical gain $g_e$ adds to the neural-drive channel and is the claim the
literature does not support.

### 4.8 Metrics

`model/metrics.py`. Two definitions are load-bearing:

$$
\text{AUC}_{\text{damage}} = \sum_n \tfrac{1}{2}\bigl(D_{n-1} + D_n\bigr)\Delta t
\quad\text{(trapezoid rule)}
$$

$$
T_{\varphi} = \min\bigl\{\, t \ :\ I(t) \ge I_0 + \varphi\,(I_{\max} - I_0)\,\bigr\}
$$

So `time_to_50pct_repair_hours` is the first time the *recovered fraction of the
original damage* reaches a half — **not** the time integrity crosses 0.5. Those
differ whenever $I_0 \ne 0$, and using the sloppy definition makes scenarios with
different starting injuries incomparable. $T_{\varphi}$ is `null` when the run
never gets there; a missing value is rendered as an em dash, never as `0`.

$$
\text{attributable fraction} =
\frac{\sum_n (R_{\text{total}} - R_{\text{base}})\,\Delta t}
     {\sum_n R_{\text{total}}\,\Delta t}
$$

## 5. Symbol to parameter key

| Symbol | Parameter key | Unit (declared) | Default |
| --- | --- | --- | --- |
| $I_0$ | `tissue.initial_integrity` | fraction | 0.20 |
| $I_{\max}$ | `tissue.max_integrity` | fraction | 1.0 |
| $k_{rep}$ | `subconscious.base_repair_rate` | integrity/hour | 0.02 |
| $k_{gf}$ | `subconscious.growth_factor_production` | field-units/hour | 0.45 |
| $g_d$ | `subconscious.damage_signal_gain` | dimensionless | 0.80 |
| $K_{gf}$ | `subconscious.gf_half_saturation` | field-units | 0.50 |
| $k_{cy}$ | `subconscious.cytokine_production` | field-units/hour | 0.30 |
| $\lambda_c$ | `mediator.<channel>.decay_per_hour` | 1/hour | 0.12 / 0.25 / 0.35 / 0.50 / 0.90 |
| $k_{nd}$ | `conscious.neural_drive_gain` | field-units/hour | 1.0 |
| $j$ | `conscious.neural_drive_jitter` | field-units/hour | 0.0 |
| $\lambda$ | `conscious.neural_drive_coupling` | dimensionless | 0.75 |
| $A_{\text{budget}}$ | `conscious.attention_budget` | fraction | 1.0 |
| $\delta$ | `conscious.attention_drain_per_hour` | 1/hour | 0.18 |
| $r$ | `conscious.attention_recovery_per_hour` | 1/hour | 0.24 |
| $\theta_f$ | `conscious.fatigue_threshold` | fraction | 0.25 |
| $\theta_r$ | `conscious.resume_attention` | fraction | 0.75 |
| $k_p$ | `conscious.perceived_gain` | dimensionless | 1.0 |
| $b$ | `conscious.perceived_bias` | fraction | 0.0 |
| $b_J$ | `module.inflammation.baseline` | fraction | 0.25 |
| $\rho$ | `module.inflammation.repair_inhibition` | dimensionless | 0.50 |
| $s_J$ | `module.inflammation.settling_rate` | 1/hour | 0.50 |
| $b_P$ | `module.perfusion.baseline` | fraction | 0.55 |
| $v$ | `module.perfusion.vasodilation_gain` | fraction | 0.40 |
| $r_P$ | `module.perfusion.response_rate` | 1/hour | 0.60 |
| $a_c$ | `module.circadian.amplitude` | fraction | 0.15 |
| $T_c$ | `module.circadian.period_hours` | hour | 24.0 |
| $g_{par}$ | `module.autonomic.parasympathetic_gain` | dimensionless | 0.30 |
| $g_{perf}$ | `module.autonomic.perfusion_gain` | fraction | 0.25 |
| $g_e$ | `module.expectancy.gain` | dimensionless | 0.0 |
| $p_e$ | `module.expectancy.perception_gain` | dimensionless | 0.0 |

Several symbols in section 4 ($D$, $A$, $N$, $G$, $J$, $C$, $\Pi$, $E$, $u$,
$\alpha$, $S(G)$, $R_{\text{base}}$, $R_{\text{total}}$, $T$) are state or derived
quantities rather than parameters, and have no key.

## 6. Which parameters have empirical support

Grades are defined in [provenance.md](provenance.md). The summary, as printed by
`cs-sim parameters`:

| Grade | Count | Meaning |
| --- | ---: | --- |
| `measured` | 0 | Nothing in this project has been measured. |
| `literature` | 1 | `module.circadian.period_hours` — the existence of a ~24 h human circadian period. |
| `assumed` | 26 | Chosen for convenience. A free knob. |
| `invented` | 7 | Taken from the source design document. No empirical support at all. |
| **Total** | **34** | **33 carry no empirical support.** |

> Conclusions that depend on `assumed` or `invented` parameters are properties of
> the model, not findings about biology. `cs-sim sensitivity` ranks the
> unsupported parameters by how much the headline metric moves when each is
> perturbed — which is a measure of how much the model depends on a guess.

### Full parameter table

| Parameter key | Default | Unit | Range | Grade |
| --- | ---: | --- | --- | --- |
| `conscious.attention_budget` | 1.0 | fraction | 0 – 1 | assumed |
| `conscious.attention_drain_per_hour` | 0.18 | 1/hour | 0 – 10 | assumed |
| `conscious.attention_recovery_per_hour` | 0.24 | 1/hour | 0 – 10 | assumed |
| `conscious.fatigue_threshold` | 0.25 | fraction | 0 – 1 | assumed |
| `conscious.neural_drive_coupling` | 0.75 | dimensionless | 0 – 100 | **invented** |
| `conscious.neural_drive_gain` | 1.0 | field-units/hour | 0 – 100 | **invented** |
| `conscious.neural_drive_jitter` | 0.0 | field-units/hour | 0 – 100 | **invented** |
| `conscious.perceived_bias` | 0.0 | fraction | −1 – 1 | assumed |
| `conscious.perceived_gain` | 1.0 | dimensionless | 0 – 10 | assumed |
| `conscious.resume_attention` | 0.75 | fraction | 0 – 1 | assumed |
| `mediator.atp.decay_per_hour` | 0.35 | 1/hour | 0 – 10 | assumed |
| `mediator.cytokine.decay_per_hour` | 0.25 | 1/hour | 0 – 10 | assumed |
| `mediator.growth_factor.decay_per_hour` | 0.12 | 1/hour | 0 – 10 | assumed |
| `mediator.neural_drive.decay_per_hour` | 0.90 | 1/hour | 0 – 10 | assumed |
| `mediator.perfusion.decay_per_hour` | 0.50 | 1/hour | 0 – 10 | assumed |
| `module.autonomic.parasympathetic_gain` | 0.30 | dimensionless | 0 – 10 | assumed |
| `module.autonomic.perfusion_gain` | 0.25 | fraction | 0 – 10 | assumed |
| `module.circadian.amplitude` | 0.15 | fraction | 0 – 1 | assumed |
| `module.circadian.period_hours` | 24.0 | hour | 1 – 168 | **literature** |
| `module.expectancy.gain` | 0.0 | dimensionless | 0 – 10 | **invented** |
| `module.expectancy.perception_gain` | 0.0 | dimensionless | 0 – 10 | **invented** |
| `module.inflammation.baseline` | 0.25 | fraction | 0 – 1 | assumed |
| `module.inflammation.repair_inhibition` | 0.50 | dimensionless | 0 – 1 | assumed |
| `module.inflammation.settling_rate` | 0.50 | 1/hour | 0 – 100 | assumed |
| `module.perfusion.baseline` | 0.55 | fraction | 0 – 10 | assumed |
| `module.perfusion.response_rate` | 0.60 | 1/hour | 0 – 100 | assumed |
| `module.perfusion.vasodilation_gain` | 0.40 | fraction | 0 – 10 | assumed |
| `subconscious.base_repair_rate` | 0.02 | integrity/hour | 0 – 1 | **invented** |
| `subconscious.cytokine_production` | 0.30 | field-units/hour | 0 – 10 | assumed |
| `subconscious.damage_signal_gain` | 0.80 | dimensionless | 0 – 10 | assumed |
| `subconscious.gf_half_saturation` | 0.50 | field-units | 1e−06 – 100 | assumed |
| `subconscious.growth_factor_production` | 0.45 | field-units/hour | 0 – 10 | assumed |
| `tissue.initial_integrity` | 0.20 | fraction | 0 – 0.99 | **invented** |
| `tissue.max_integrity` | 1.0 | fraction | 0.01 – 1 | assumed |

The 7 `invented` grades are all traceable to the source design document:
`tissue.initial_integrity` (the "80% damage" case, expressed as integrity),
`subconscious.base_repair_rate` (its `0.5` per tick, rescaled per hour),
`conscious.neural_drive_gain` and `conscious.neural_drive_jitter` (its random
`1.0–3.0` boost), `conscious.neural_drive_coupling` (the mind-over-tissue claim
itself), and the two expectancy gains (a module the source implies but never
separated from attention).

### What overriding does

`ParameterSet.with_overrides` — used by `--set` on the CLI and by scenario
`overrides` — replaces a value **and downgrades its grade to `assumed`**, with a
note naming the previous value. A value chosen at runtime is not traceable to its
original source, so keeping the original flattering tag would be exactly the
dishonesty the provenance system exists to prevent. This also means a conclusion
that only holds when a value is passed with `--set` rests on an `assumed`
parameter, whatever the default's grade was.

## 7. What is not modelled

Named here so that nobody has to infer it from an absence:

- **No geometry.** One scalar integrity value for a whole "tissue".
- **No cell populations, no fibre orientation, no scar formation, no re-injury.**
- **No immune cell trafficking**; inflammation is a single scalar with one
  suppressive term.
- **No pharmacokinetics, no dosing, no interventions.**
- **No subject, no population, no measurement, no clinical endpoint.**
- **No cost function or calibration** against any observed healing curve.
- **No placebo/nocebo dynamics in the physical path**; expectancy defaults to off.
- **No bidirectional hardware path.** Adapters are read-only with respect to the
  wearer; there is no stimulation, actuation or write method anywhere in the
  codebase, and that is a deliberate safety boundary rather than a missing
  feature.
- **No medical function of any kind.**

## 8. Determinism and digests

Three digests are reported for every run (`SimulationResult`):

| Digest | Covers |
| --- | --- |
| `parameter_digest` | The full parameter set including provenance, units and bounds — so a run with the same numbers but a different grade is distinguishable. |
| `config_digest` | `RunConfig.as_dict()`: scenario, seed, step, horizon, tissue, focus policy, module list, overrides. |
| `run_digest` | The two digests above plus the metrics summary and the final integrity. |

Randomness is confined to named substreams derived by SHA-256 from the root seed
(`core/rng.py`), so adding a module cannot perturb a previously reproduced run.
`hash()` is deliberately not used, because it is salted per process.
`conscious.neural_drive_jitter = 0.0` means the default configuration draws no
random numbers at all, which is why the CI determinism job can assert
byte-identical output from two invocations.
