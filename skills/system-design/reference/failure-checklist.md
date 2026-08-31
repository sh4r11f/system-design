# Failure Analysis Checklist

Run this against the architecture diagram. A design is not done when it works on the happy
path; it is done when every question here has an answer written down. "No reply" always has
five explanations (request lost / request queued / remote dead / remote slow / reply lost)
and the sender cannot tell them apart — design accordingly.

## For every arrow (call, message, replication stream)

- **Slow**: what timeout applies? What happens at the timeout — fallback, error, retry?
  Whose latency budget absorbs it? (Sequential chains stack tails; fan-out amplifies them.)
- **Lost**: is the operation retried? Then name the **idempotency key** — a retry without
  one is a duplicate generator (double emails, double charges).
- **Duplicated**: the network and at-least-once delivery both duplicate; is the consumer
  idempotent? Where does the dedup record live — ideally in the *same* transactional store
  as the side effect?
- **Stale**: is this data derived/cached/replicated? What is the staleness budget, and which
  user-facing feature notices first (read-your-writes violations top the list)?
- **Reordered**: messages arrive out of order; is ordering assumed anywhere it isn't
  guaranteed (only per-partition/per-key order exists)? Buffer, sequence, or relax.

## For every box (service, store, node)

- **Dies**: failover story? What was acknowledged-but-not-yet-replicated at death (async
  replication loses acked writes on failover — decide if that's acceptable)?
- **Pauses and returns** (GC, VM migration): the zombie test — it still believes it holds a
  lease/leadership it lost. Check-then-act is broken; safety must be enforced **at the
  resource** via fencing tokens / CAS, not by the node's self-belief.
- **Lies subtly** (clock skew): is wall-clock time used for ordering, conflict resolution
  (LWW silently discards causally-newer writes), or lease math? Monotonic clocks are for
  local durations only; cross-node order needs logical clocks or a leader.
- **Restarts empty** (cache node, consumer): cold-start behavior? Rebuild path? Thundering
  herd / dogpile protection on the store behind it?

## Correlated failure hunt

List every dependency shared by "redundant" components: region/AZ, top-of-rack switch,
config source, secret/cert store and its expiry, deploy pipeline (same bad version pushed
everywhere), shared library, DNS, the single on-call human. For each: what is its
availability, and what happens when it fails *everywhere at once*? Availability is capped by
the least-available shared dependency. Software bugs and bad config are inherently
correlated — the defenses are staged rollouts, canaries, fast rollback, and isolation, not
more replicas.

## Overload & cascade

- Where does load shed **first**? (If the answer is "nowhere", the answer is "everywhere,
  at once, at the worst time".) Rate limits per client/tenant; bounded queues everywhere
  (an unbounded queue is a latency bomb with a memory fuse); backpressure propagated
  upstream.
- The cascade mechanism to check for: dependency slows → callers' in-flight work grows
  (L = λW) → their pools exhaust → the outage spreads. Defenses: timeouts + circuit
  breakers + shedding, and utilization headroom (60–75%).
- Retry storms: retries multiply load exactly when capacity is least available — cap with
  budgets, exponential backoff + jitter, and never retry non-idempotent ops blindly.

## Degradation ladder (write it as a table)

For overload ×2 and ×10, and for each major dependency down: what mode does the system enter,
what does the user experience, what is deliberately dropped (freshness? personalization?
non-critical writes?), and what is never dropped. Fail-open vs fail-closed is a per-endpoint
decision made in daylight (e.g., serving reads without the rate limiter: open; accepting
writes without auth: closed). Fallbacks are feature contracts with **bounded, priced**
degradation — compute the cost so the design defends itself.

## Recovery & operations

- **Rollback**: one command? Requires immutable versioned artifacts, config as data, and —
  for anything derived — knowing what must be re-derived after rolling back.
- **Restore**: backups exist AND have been restored recently (an unrestored backup is a
  hope, not a plan). What is rebuildable from the retained event log vs gone forever?
- **Blast radius**: can one tenant/key/partition take down the rest? Bulkheads, per-tenant
  quotas, whale-tenant plan.
- **Observability minimums**: rate, errors, duration (percentiles, never averages) per
  endpoint; saturation per resource; queue depths and consumer lag; replication lag;
  cache hit rate; and *business-level* canaries (orders/min) that catch what infra metrics
  miss. Alert on symptoms (SLO burn), page on user impact, and make every alarm actionable
  — 10 daily false alarms is a disabled pager.
- **The acknowledged-write question**, asked verbatim: "after we tell the user 'saved',
  what sequence of single failures loses that data?" If the answer is short, decide whether
  the business accepts it — in writing.
