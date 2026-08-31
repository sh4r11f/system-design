# Decision Tables

Format: **choose it when / the price / watch for**. Every choice is a trade; state it as
"X buys A at the price of B". When two rows tie, take the boring one your team already runs.

## Data model

| Model | Choose when | Price | Watch for |
|---|---|---|---|
| Relational | Many-to-many relationships; ad-hoc queries not known in advance; write-time integrity (constraints, FKs) | Joins + object-relational mismatch; migrations | N+1 query patterns at the app layer |
| Document | Data is self-contained trees (order+items, profile+posts); read locality; per-record schema flexibility | App-side joins; many-to-many is painful; schema-on-read shifts validation to readers | Denormalized copies → update anomalies: every copy needs a designed repair path |
| Graph | Variable-depth traversals are the product (paths, networks, recommendations) | Weaker aggregate/OLAP story; operational maturity varies | Doing graphs in SQL: fixed-depth joins & fragile recursive CTEs |

Denormalization is a *decision*, not a model property: it buys reads by making every future
write responsible for every copy. Make it only with the repair path designed. Store stable
IDs, not display values.

## Storage engine (beneath whatever database you pick)

| Engine | Choose when | Price | Watch for |
|---|---|---|---|
| LSM-tree (RocksDB, Cassandra…) | Write-heavy; recent-data reads; sequential-I/O-friendly | Read amplification (many levels; blooms mitigate); compaction debt | Compaction falling behind under write bursts → reads slow + disk fills |
| B-tree (Postgres, InnoDB…) | Read-heavy; point + range lookups; predictable latency | Write amplification (page rewrites); needs WAL | p99 lives in checkpoint/fsync behavior and page-cache hit rate |
| Columnar (Parquet, warehouses) | Analytics: scan millions of rows, few columns | Slow point writes; batch-oriented ingestion | Sort key choice = which queries are fast AND how well it compresses |

Amplification triangle: every engine trades write amp / read amp / space amp — know which
one your workload can afford.

## Replication architecture

| Architecture | Choose when | Price | Watch for |
|---|---|---|---|
| Single-leader | Default. Simplest guarantee-per-machinery ratio; can be strong (sync/consensus-backed) | Failover is fraught (split brain, lost async writes); writes limited to one node/region | Async ack = "saved" is probabilistic; replication-lag anomalies (see below) |
| Multi-leader | Writes must be local in several regions; offline clients; collaborative editing | **Write conflicts are inherent** — budget real merge engineering | LWW resolves conflicts by silently destroying data; clock skew makes it worse |
| Leaderless (quorums, R+W>N) | Availability/latency dominate; data merges naturally (carts, counters, sets) | Eventual consistency; quorum overlap ≠ linearizability; version vectors needed | Sloppy quorums + hinted handoff quietly forfeit the overlap guarantee |

Replication-lag anomalies and their per-feature fixes: **read-your-writes** (route by
last-write LSN/token), **monotonic reads** (sticky replica per user), **consistent prefix**
(co-partition causally related data). Choose guarantees per feature, not globally.

## Partitioning

| Scheme | Choose when | Price | Watch for |
|---|---|---|---|
| Key-range | Range scans matter (time series per entity) | Skew: monotonic keys hammer the last partition | Timestamp-prefixed keys = one hot partition taking 100% of writes |
| Hash | Balance by default | Range queries become scatter-gather | Never `hash % N` — adding a node reshuffles ~everything |
| Compound (hash(entity), range(time)) | Both balance and per-entity ranges | Key design effort | Whale entities (hot tenants) still skew |

Rebalancing: consistent hashing with virtual nodes, or fixed-many-partitions moved whole —
moved data must be ∝ cluster change, not cluster size. A single hot key defeats placement:
salt hot **writes** (pre-vetted salts covering distinct partitions), cache hot **reads**.
Secondary indexes: local (cheap writes, scatter-gather reads) vs global/term-partitioned
(one-partition reads, fan-out + usually async writes).

## Transactions & isolation

| Level | Stops | Still allows | Use |
|---|---|---|---|
| Read committed | Dirty reads/writes | Read skew, lost update, write skew | Floor; know what's yours to handle |
| Snapshot isolation | + read skew; first-committer-wins stops lost updates | **Write skew, phantoms** | Read-mostly correctness; long reads block nobody (MVCC) |
| Serializable (SSI/2PL/serial) | Everything | — (pay in aborts or blocking) | Invariants the DB must enforce: bookings, balances, uniqueness |

Optimistic concurrency makes **retry a first-class code path**. Phantom-shaped invariants
("no overlapping booking") need serializable, a unique constraint, or **materializing the
conflict** into a row to fight over. Lost updates alternatively: atomic ops, CAS,
`SELECT FOR UPDATE`.

## Consistency & coordination

Need **linearizability** (single-copy behavior) only for: locks/leases/leader election,
uniqueness claims, cross-channel recency. It costs coordination on every operation —
cross-region, that's a WAN round trip *every time* (PACELC), partition or no partition.
Everything else: eventual + per-feature guarantees above.

Ordering without clocks: Lamport timestamps for a total order; version vectors to *detect*
concurrency. Never order cross-node events by wall clock. A node's belief about its own role
(leader, lock holder) can always be stale — enforce at the resource with **fencing tokens**.
Need consensus? Use ZooKeeper/etcd or a Raft-inside database; do not build it. 2PC solves
atomic commit, not agreement, and blocks on coordinator failure — modern systems run 2PC
*over* consensus-replicated participants.

## Integration: batch, streams, derived data

- One **system of record**; everything else (indexes, caches, warehouses, feeds) is
  **derived data** maintained by consumers of an ordered log — because dual writes to
  parallel stores cannot be made consistent (no single order exists).
- Log-based brokers (Kafka model) when history/replay/fan-out matter; classic queues for
  task distribution where messages die on ack.
- Delivery: commit-offset-first loses; process-first duplicates ⇒ **at-least-once +
  idempotent consumers = effectively once**. Every consumer names its idempotency key.
- Event time ≠ processing time: windows need watermarks; lateness slack trades latency for
  completeness; late data needs a designed path.
- The payoff of log-centric design: new views backfilled from history; bugs fixed by
  rebuild-and-swap; blue-green view migrations. The price: **timeliness** — views lag;
  cross-view reads can see skew; transactions across views don't exist.
- Escape the dual-write bug at the source: **outbox pattern** (event row committed in the
  same DB transaction, CDC publishes it).

## Caching

Cache when: read-heavy, tolerable staleness, skewed popularity (Zipf makes small caches
mighty: ~5% of keys can serve most traffic). Decide explicitly: eviction (LRU default),
invalidation (event-driven from the log > TTL > manual), staleness budget per feature,
**dogpile protection** (request coalescing, soft-TTL) and cold-start warming. A cache is
derived data: it must be rebuildable, never authoritative.

## Encoding & schema evolution

Schema-driven binary (Protobuf/Avro) for anything stored long or crossing service
boundaries. Rules that keep rollouts boring: new fields always optional/defaulted; never
reuse or renumber tags; Avro-style changes only with defaults; check compatibility **in CI
both directions** (rolling upgrades mean old and new code always coexist). JSON at the
edges is fine; JSON as a contract is not (2⁵³ integer trap, no schema).

## Rate limiting & IDs (edge concerns that are really architecture)

- Token bucket: bursty clients, cap the average (the default). Sliding-window counter:
  strict contracts. Fixed windows: 2× burst hole at boundaries — avoid. Distributed
  limiting: per-node buckets over-admit N×; central store pays a hop — choose knowingly.
  Load shedding is triage: a 429 for one client buys p99 for the rest. Decide per endpoint
  whether the limiter fails open or closed.
- IDs: sequential (compact; enumerable + hot-tail), snowflake (coordination-free,
  k-sortable; refuses on clock regression — handle it), random (unguessable, uniform;
  needs put-if-absent collision handling at scale). Never expose raw sequences publicly.
