---
name: system-design
description: Principled planning and review of software, data, and ML system architectures. Applies a numbers-first method - requirements with explicit targets, back-of-envelope workload estimation, component design with named guarantees and their costs, systematic failure analysis, and evolution planning - plus ML-specific discipline (leakage audits, serving modes, drift monitoring, retraining loops). Use when designing or architecting a system, service, pipeline, or ML system; when choosing between databases, queues, caches, replication/partitioning schemes, or serving strategies; or when reviewing an existing architecture or design document.
---

# Principled System Design

Produce designs that state **numbers, not adjectives**; that name every **guarantee with its
price**; and that are only "done" when the **failure** and **evolution** questions have honest
answers. Prefer boring technology; make every piece of complexity earn its place; start
without ML and make ML earn its replacement of the baseline.

Reference files in this skill's directory (read only what the task needs):

- `reference/estimation.md` — latency ladder, conversion tricks, Little's law, queueing,
  tail math, availability arithmetic, scalability laws. Read before any Step 2.
- `reference/decision-tables.md` — choose-when/price/watch-for tables: data models, storage
  engines, replication, partitioning, isolation, consistency, integration, caching, encoding,
  rate limiting, ID generation. Read when making or judging a technology/architecture choice.
- `reference/failure-checklist.md` — the failure interrogation and the mitigation catalog.
  Read before any Step 4 and for every review.
- `reference/ml-systems.md` — framing, labels, leakage audit, evaluation gates, serving,
  drift monitoring, retraining, feedback loops. Read whenever the system contains (or the
  user proposes) a learned component.

## Scale the effort to the ask

- **Single choice** ("which database/queue/cache?", "SQL or NoSQL here?"): pull the relevant
  decision table, get the 2–3 workload numbers that decide it (estimate them if the user
  didn't supply them, and say so), give one recommendation with its price and its watch-fors.
  A few paragraphs, not a document.
- **Component design** (a rate limiter, an ingestion path, a feature store): compact doc —
  requirements table, mini-estimate, chosen design with guarantees/costs, failure notes.
- **Full system design**: the complete method and output template below.
- **Review** of an existing design/architecture: skip to Review mode.

When the design targets an existing system, first read what already exists in the repository
(stores, queues, infra config, deployment) — the design must integrate with reality, and
"what they already run well" is a strong argument for boring continuity. If the repo contains
no relevant infrastructure (or there is no repo), note that, state the assumed stack in the
assumptions ledger, and move on.

## The method (design mode)

Work the five steps in order. Do not present architecture before the estimate exists.

### Step 1 — Requirements

Functional requirements as a short list. Non-functional requirements as a table with
**numbers**: p50/p99 latency targets, availability, durability, consistency/freshness needs,
throughput, data volume — plus cost ceilings and compliance/privacy rows *only when they
constrain the design* (skip rows that don't apply rather than inventing decoration; an
invented-but-load-bearing number goes in the assumptions ledger like any other). If the user
gave adjectives ("fast", "highly available"), convert each to a defensible number and record
it in the **assumptions ledger**. Ask the user only when the answer would flip the
architecture (e.g., "can a confirmed write ever be lost?"); otherwise assume, state, and
proceed.

### Step 2 — Workload estimation

Read `reference/estimation.md`. Deliver: reads/s and writes/s (average and peak), read:write
ratio, data size now and in 2 years, working-set size, fan-out, hot-key/skew profile,
bandwidth. Then the paragraph that matters: **"what these numbers decide"** — fits-on-one-box
or not, cache-worthy or not, partition-worthy or not, CDN or not. Most bad designs die here,
cheaply; let them.

### Step 3 — Design

Compose standard blocks (database, cache, index, queue/log, batch/stream processor). Consult
`reference/decision-tables.md` for each choice. For **every component** state four things:
its role, the guarantee it provides, the price it pays for that guarantee, and what it must
NOT be trusted for. Identify the **system of record** and mark everything else as **derived
data** (rebuildable from it); never design dual writes to parallel stores — create one
ordered truth and let other stores follow it. State consistency guarantees **per user-facing
feature** (read-your-writes here, eventual there), not as one global label. Include a mermaid
diagram of components and data flow; distinguish read and write paths within mermaid's
means (e.g., solid vs dashed arrows plus a one-line legend).

### Step 4 — Failure analysis

Read `reference/failure-checklist.md`. For every arrow in the diagram ask: what if it is
slow, lost, duplicated, stale, reordered? For every box: what if it dies, and what if it
*pauses and comes back believing it holds a role it lost*? Hunt **correlated failures**
(shared region, config, cert, deploy pipeline, library, secret store) — availability is
capped by the least-available shared dependency, and redundancy does not fix correlated
faults. Produce a failure table (failure / detection / blast radius / mitigation) and a
**degradation ladder**: what sheds first, what the system does at 2× and 10× overload, and
what the user experiences in each mode. Every "retry" must name its idempotency key; every
"timeout" its fallback.

### Step 5 — Evolution

Multiply each load parameter by 10 independently; name what breaks first and the migration
path (live resharding, blue-green view rebuilds, schema evolution rules). State what is
rebuildable from retained raw history and what is irreversibly lost if wrong. Note which
decisions are cheap to reverse (do them now) vs expensive (spend the analysis there).

### ML extension

If the system contains a learned component, read `reference/ml-systems.md` and add the ML
section of the template. Non-negotiables to enforce: a heuristic baseline that ML must
measurably beat; labels defined like an API contract; a leakage audit; **one feature
definition serving both training and serving** (point-in-time replay for training); an
evaluation gate beyond a single average metric; a monitoring plan that respects label delay;
and an answer to "does this system influence its own future training data?" (if yes: budget
exploration and log propensities from day one).

## Output template (full design)

1. **Summary** — the problem, the shape of the solution, the top 3 risks. ≤ 8 sentences.
2. **Requirements** — functional list; non-functional table (all numbers).
3. **Assumptions ledger** — every number or constraint invented on the user's behalf.
4. **Workload estimate** — the figures + "what these numbers decide".
5. **Architecture** — mermaid diagram + component table (component / role / guarantee /
   price / not to be trusted for).
6. **Data** — system of record; derived views and how each is kept consistent (and rebuilt);
   schema + evolution/compatibility plan; per-feature consistency guarantees.
7. **Failure analysis** — failure table + degradation ladder + correlated-failure findings.
8. **Evolution** — 10× analysis, migration paths, reversible-vs-irreversible ledger.
9. **ML systems plan** — only when applicable; per `reference/ml-systems.md` §"Plan sections".
10. **Rejected alternatives** — each in one line with the reason (prevents relitigating).
11. **Open questions** — only ones whose answers change the design.

Tables for enumerable facts; prose for reasoning. State trade-offs as "X buys A at the price
of B", never "X is better".

## Review mode

When given an existing design, architecture, or design document to review: read
`reference/failure-checklist.md` (and `reference/ml-systems.md` if ML is present), then audit
against this skill's rules. Report findings **ordered by severity**:

- **Blocker** — violates a correctness/durability requirement or a physics limit (e.g.,
  dual writes as source of truth, LWW on data that must not be lost, cross-region sync call
  inside a 50 ms budget, offline-only validation of an ML system, no idempotency on a
  retried money path).
- **Major** — will cause incidents or rewrites at stated scale (hash-mod-N placement, one
  global consistency label, unbounded queues, no degradation plan, leakage-suspect features,
  no rollback story).
- **Minor** — costs or cleanliness (over-provisioned guarantees, exotic tech where boring
  fits, missing observability detail).

Each finding: what the design says → which principle it breaks → the concrete fix. Also
verify the positives: say explicitly which parts are sound, so the review is a map, not a
list of complaints. If the document has no numbers, that is finding #1 — a design without an
estimate is a mood board.

## Anti-patterns — flag on sight

- Adjectives where numbers belong; architecture chosen before any estimate.
- Dual writes to parallel stores; no identified system of record.
- "Eventually consistent" or "strongly consistent" as a single global label.
- `hash % N` placement; timestamps (wall clocks) used for ordering or conflict resolution.
- Retries without idempotency keys; timeouts without fallbacks; unbounded queues; no
  backpressure or load shedding; check-then-act on distributed state without fencing.
- Redundancy claims that ignore correlated failure; availability math on a serial chain
  presented as the parallel formula.
- Caching without an invalidation/staleness story; celebrity/hot-key blindness.
- ML: no baseline; random splits over time-drifting data; features computed two ways for
  training vs serving; accuracy on imbalanced problems; 0.5 thresholds where costs are
  asymmetric; no monitoring or retraining plan; ignoring that the model shapes its own
  training data.
- "We'll add monitoring/rate limiting/schema management later."
