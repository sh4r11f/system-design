# Estimation Reference

Goal: order of magnitude, ±3×. A 10× error changes architectures; a 2× error rarely does.
Never present two significant figures — that precision is a lie. (This applies to
*estimates*; configuration constants — timeouts, retry counts, TTLs — are chosen
parameters, not estimates: state them exactly.)

## The latency ladder (rounded 2020s numbers; the *ratios* are the knowledge)

| Operation | Cost | ×RAM ref |
|---|---|---|
| L1 cache reference | 1 ns | 0.01× |
| Main-memory reference | 100 ns | 1× |
| Read 1 MB sequentially from RAM | 3 µs | — |
| NVMe SSD random read | 20 µs | 200× |
| Read 1 MB sequentially from NVMe | 200 µs | — |
| Round trip inside a datacenter | 250 µs | 2,500× |
| HDD seek | 4 ms | 40,000× |
| Read 1 MB sequentially from HDD | 6 ms | — |
| Round trip, same continent | 20 ms | 200,000× |
| Round trip, cross-continent | 140 ms | 1,400,000× |

Rules that fall out of the ladder:

- **Caching works**: RAM beats SSD ~1000× and a WAN round trip ~10⁶×.
- **Batching works**: one DC round trip ≈ 10 SSD reads. Never make N network calls where one
  call carrying N items will do (the N+1 query bug, quantified).
- **Sequential beats random on every medium** — the physics behind logs, LSM-trees, and
  columnar scans.
- **Geography is unfixable**: 140 ms cross-continent yields only to moving data closer
  (CDN, geo-replicated reads), never to code.

## Conversion tricks

- A day ≈ **10⁵ seconds** → "N per day" ≈ N ÷ 100,000 per second.
- **Peak = 2–5× average**; default 3×.
- Storage = rate × item size × retention × replication (default replication 3×).
- Bandwidth: bytes/s × 8 = bits/s. Tens of Gbit/s of media egress ⇒ CDN, not servers.
- Sanity anchor: **100 M users × 1 KB = 100 GB — fits in RAM on one large box.** Metadata is
  almost always smaller than intuition says; *media and event streams* are what explode.
  Estimate before you distribute.

## Little's law — L = λW

Items in flight = arrival rate × time inside. Sizes anything that holds work: thread pools,
connection pools, queue memory, in-flight request buffers. It is also the outage mechanism:
a dependency slows → W grows → L grows → pools exhaust → the outage spreads. Defenses:
timeouts, backpressure, shedding.

## Queueing — why systems melt before 100%

M/M/1 shape: wait ∝ ρ/(1−ρ). Utilization 0.5 → 0.9 multiplies queueing delay ~6–11×; the
p99 grows faster than the mean. **Plan for 60–75% utilization** — the last quarter of
"capacity" is latency poison, and headroom is a feature you buy for the p99. Variance is the
enemy: bound request sizes, split huge jobs.

## Tail latency

- Fan-out amplification: P(request touches a p-slow backend) = **1 − (1−p)^N**.
  At p = 1% and N = 100: 63% of requests. Median-of-max(100 draws) ≈ single-node p99.3 —
  at high fan-out the tail *is* the typical experience.
- Sequential call chains stack their tails; parallelizing trades stacking for fan-out
  amplification — compute both before choosing.
- **Hedged requests**: fire a duplicate once the original passes ~p95; take the first
  answer. ~5% extra load for a large p99 cut. Works because real tails are transient
  per-server hiccups (GC, queueing) that the second server won't share.

## Availability arithmetic

- Serial chain (all must be up): A = ∏aᵢ — chains degrade; adding a 99.5% dependency to a
  99.95% path costs more than everything else combined.
- Parallel replicas (any one suffices): A = 1 − ∏(1−aᵢ) — **valid only for independent
  faults**.
- **Correlated cap**: availability ≤ the least-available *shared* dependency (switch,
  region, config source, deploy pipeline, cert authority). Redundancy cannot fix software
  bugs or bad config pushes — those hit every replica at once.
- Nines: 99% = 3.7 d/yr · 99.9% = 8.8 h/yr · 99.99% = 53 min/yr · 99.999% = 5.3 min/yr.
- SLO error budget: (1 − SLO) × period; e.g. 99.9%/30 d = 43.2 minutes.

## Scalability laws

- **Amdahl**: serial fraction σ caps speedup at 1/σ forever.
- **USL**: X(N) = N·X(1) / (1 + σ(N−1) + κN(N−1)); coherence κ (pairwise coordination)
  makes throughput **peak and then fall**, at N\* = √((1−σ)/κ). Diagnose from measurements:
  high σ → shard the serial thing (single leader, global lock); high κ → coordinate less
  (smaller quorums, partition so nodes needn't agree).

## Deliverable of an estimation pass

Reads/s and writes/s (avg + peak), read:write ratio, data size now and +2 years, working-set
size, fan-out per request, hot-key profile, bandwidth — followed by 3–5 sentences of **what
these numbers decide** (one box or many; cache or not; partition or not; CDN or not; which
single number is the design's hard problem).
