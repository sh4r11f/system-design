# ML Systems Reference

An ML system is a data system with a learned component: the model is ~10% of the design and
~100% of the mystique. Everything below assumes the data-systems discipline already applies
(logs, derived data, idempotency, monitoring).

## Before any model

- **Should this be ML at all?** ML earns its complexity only when: patterns exist and are
  too complex for rules, data is available or collectable, wrong predictions are tolerable
  at some rate, the decision repeats at scale, and the patterns change. If a formula or a
  simple heuristic captures 90% of the value, ship that.
- **Baseline ladder is mandatory**: chance → the heuristic the business would use anyway →
  linear model → tree ensemble. Each rung must beat the previous on the tracked metric to
  justify its complexity; "we can't beat the heuristic" is a legitimate, money-saving
  finding. Most tabular value arrives by rung three.
- **Framing is a product decision in math**: likelihood vs urgency vs value-at-risk
  framings act on *different people* under the same budget. Write down what the prediction
  will be *used for* before choosing the target.
- **The label is designed, not found**: window lengths, edge cases, and definitions change
  the ground truth itself. Write label definitions like API contracts. Where do labels come
  from (natural/delayed, annotators + agreement measurement, weak supervision, active
  learning under a budget) and how late do they arrive? **Label delay** shapes the whole
  monitoring/retraining design later — record it now.

## Data & features

- Sampling: bias beats volume — no sample size fixes selecting on the outcome (activity,
  approval). Sample the unit you predict about; stratify what must be represented.
- Imbalance: accuracy is a broken instrument; live in precision/recall space, reweight or
  resample, and set thresholds by cost (below). These reshape errors; only better
  features/data reduce them.
- **The leakage audit** — run for every feature:
  1. *Post-outcome*: at prediction moment, is this value already written — and would it
     have this value if the outcome hadn't happened? (Screen: any single feature with
     near-model-level solo AUC is either great or a time traveler.)
  2. *Preprocessing contamination*: is every fitted step (scaling, imputation, selection,
     target encoding) inside the CV pipeline, fitted per training fold only?
  3. *Split honesty*: drifting world → split by time; memorizable units (user, session,
     hospital) → split by group. A lower honest score beats a higher fraudulent one — the
     honest number is the only one production pays.
- **Point-in-time correctness**: a training row may only see feature values as they were at
  that row's timestamp. Build the training set by *replaying* history through the same
  definition serving uses. The seduction to warn about: the leaky full-history builder
  often looks **identical offline** and is simpler to write — it fails only in production.
- **Train/serve skew**: one feature definition, two materializations (offline store for
  history, online store for latency). Never two implementations. Tier features by
  freshness: static → batch-refreshed → stream-updated → request-time computed; features
  whose *rate of change is the signal* (velocity counters) must update synchronously in the
  request path.

## Evaluation gates (beyond one average)

- **Calibration** (reliability curve / ECE): thresholds and expected-value math assume
  p means p; calibration is prevalence-sensitive and cheap to fix (isotonic/Platt) —
  recalibrate before declaring "model degraded".
- **Slices**: the average outvotes small segments; report the metric per platform, cohort,
  geography, protected group. A weak slice hiding in a healthy average is the default
  failure, and this table is also the first fairness audit.
- **Behavioral tests** in CI: invariance (irrelevant nudges must not swing decisions) and
  monotonic constraints ("risk may only rise with amount") — lawsuit-shaped bugs no AUC
  reveals.
- **Uncertainty**: bootstrap the metric difference; if the CI straddles zero, ship the
  simpler model. Guard the test set from leaderboard erosion (a final holdout used once).
- Reproducibility substrate: same code + data + seed = same bits; log params, data version,
  feature-definition version, seed, environment for every run.

## Decisions, not scores

The model outputs probabilities; the business executes a **policy**. Act when
p > c_fp/(c_fp + c_fn); with variable stakes, threshold per item (p\* = cost/(save_rate ×
value)). Keep thresholds, blend weights, and guardrails in config — retuning must not mean
retraining (decouple objectives: one model per objective, combined at decision time).
Review queues get capacity constraints. 0.5 is a superstition.

## Serving

- Mode: batch precompute (cheap lookups, staleness, wasted compute) vs online (fresh,
  latency-bound) vs hybrid (batch candidates + online ranking) — decide from how fast the
  input changes relative to how often it's used; fill the feature-freshness ×
  prediction-freshness 2×2 explicitly.
- **Batching is the physics**: vectorization collapses per-row cost; a dynamic batcher's
  window trades a little latency for multiplied capacity (on GPUs, mandatory).
- Compression when the envelope demands it: quantization (~8× for near-free on weights),
  pruning (ensembles front-load value), distillation (transfers only what the student can
  represent). These are the visa for edge deployment.
- **Fallbacks are feature contracts**: feature-store timeout → defaults + missingness
  indicator; model timeout → rules. Every request gets a decision inside the budget;
  degraded quality is bounded and priced in advance. Decisions on retried requests must be
  idempotent (decision cache by request key).
- Ship model + feature-pipeline version as a **matched, immutable pair** behind a router;
  rollback is a pointer flip. Paired artifacts (e.g., user/item embeddings + the ranker
  trained on them) share one version — mixed versions fail silently.

## Monitoring (the world is not i.i.d.)

- Degradation taxonomy: **covariate** shift (P(X); visible instantly in inputs and
  predictions), **label** shift (recalibrate first), **concept** drift (P(Y|X) — invisible
  to every label-free monitor; only labels can see it), and the impostor that outnumbers
  them: **pipeline failure** (nulls from a broken upstream job) — check plumbing before
  theorizing about the world.
- Detector stack, layered by information speed: PSI on the model's **prediction scores**
  (best single default) + per-feature KS/PSI (marginals only) + a domain classifier
  (catches joint shifts and names what moved) → proxy labels (reviews, complaints —
  biased; keep a random audit slice) → true labels when they mature.
- **Label delay is a hard floor** on seeing concept drift; budget it, shrink it, and let it
  set the retraining cadence. Watch alert arithmetic: 200 features × daily tests at p<0.05
  = 10 false pages/day = a disabled pager.
- **Feedback loops**: if the model influences its own future training data
  (recommendations, pricing, approvals, moderation), expect exposure to calcify into
  "truth" and selective labels to bias retraining. Non-negotiables from day one: an
  **exploration budget** (priced in real dollars) and **propensity logging** on every
  decision — there is no retroactive de-biasing without it.

## Retraining & testing in production

- Policies: never (fossilizes) / scheduled / monitor-triggered (efficient; needs the
  detector stack). All are floored by label delay + data accumulation + pipeline time —
  shortening that loop beats sharpening the model.
- Stateless retrains (from scratch on a window) are the reproducible default; stateful
  fine-tuning is cheaper at high frequency but propagates poisoned data forever and
  complicates "rebuild the March 3rd model" — hybrid: frequent fine-tunes + periodic full
  retrain from the immutable lake.
- Promotion ladder: **shadow** (real traffic, logged not served — catches crashes, skew,
  latency; free) → **canary** (1→5→25%, strict guardrail tripwires, auto-rollback; blast
  radius = stage size) → **A/B** (the measuring instrument: pre-commit the horizon —
  **peeking at daily p-values manufactures ~25% false winners** — or use sequential
  methods; randomize the unit that experiences treatment; watch interference) →
  **bandits** (Thompson sampling: cheap decisions, biased measurements — for many fast
  variants, not for numbers you must trust). Keep A/A tests running permanently.
- The registry gate (enforced, not conventional): evaluation report incl. slices,
  behavioral tests pass, beats incumbent, calibration bound, feature-version compatible
  with serving, data fresh enough, latency/size within envelope. Every gate is a
  fossilized incident.

## Plan sections (what the ML part of a design doc must contain)

1. Framing + what the prediction is used for; the baseline it must beat.
2. Label definition, source, delay; labeling strategy and budget.
3. Data & features: sources, point-in-time plan, leakage audit results, feature tiers,
   store layout (offline/online).
4. Evaluation: metrics + slices + behavioral tests + the promotion gate.
5. Decision policy: thresholds/costs, config surface, review-queue capacity.
6. Serving: mode, latency budget decomposition, fallbacks, artifact versioning.
7. Monitoring: detector stack, label-delay layers, feedback-loop answer (exploration +
   propensity logging), alert budget.
8. Retraining: policy, trigger, window, promotion ladder, rollback drill.
