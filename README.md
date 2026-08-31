# System Design Crash Course

A hands-on, deep-dive course on designing data systems and machine learning systems, in Jupyter notebooks.
The curriculum follows the material of two books — **Designing Data-Intensive Applications** (Martin Kleppmann)
and **Designing Machine Learning Systems** (Chip Huyen) — with original explanations, diagrams, and working
mini-implementations of every core mechanism, plus end-to-end capstone designs.

**The rule of the course: nothing is just described — everything is built.** You don't read about LSM-trees,
quorums, MVCC, drift detection, or A/B peeking; you implement them, break them, and watch them fail in the
exact ways the theory predicts. Every notebook is self-verifying: inline `assert`s re-check every claim on
every run.

## Course map

### Part 0 — Foundations
| # | Notebook | You learn | You build |
|---|----------|-----------|-----------|
| 00 | [Orientation](notebooks/part0-foundations/00-orientation.ipynb) | Reliability, scalability, maintainability; how to think in trade-offs | Tail-latency simulator: why p99 rules UX and fan-out amplifies the tail |
| 01 | [Scale & estimation](notebooks/part0-foundations/01-scale-and-estimation.ipynb) | Back-of-envelope math, latency numbers, Little's law, queueing, Amdahl/USL | Estimation toolkit; M/M/1 queue sim; scalability curve fitting |

### Part 1 — Data-Intensive Applications (DDIA)
| # | Notebook | You learn | You build |
|---|----------|-----------|-----------|
| 02 | [Data models](notebooks/part1-data-systems/02-data-models.ipynb) | Relational vs document vs graph; normalization; query languages | One social app modeled three ways: SQLite, JSON documents, toy graph store |
| 03 | [Storage engines](notebooks/part1-data-systems/03-storage-engines.ipynb) | Logs, hash indexes, SSTables/LSM-trees, B-trees, bloom filters, column storage | A Bitcask-style store, then a mini LSM-tree with compaction; row-vs-column benchmark |
| 04 | [Encoding & evolution](notebooks/part1-data-systems/04-encoding-evolution.ipynb) | JSON/Avro/Protobuf, schema evolution, forward/backward compatibility | A binary codec + Avro-style schema resolution; compatibility test matrix |
| 05 | [Replication](notebooks/part1-data-systems/05-replication.ipynb) | Leader-based, multi-leader, leaderless; replication lag anomalies; quorums | Replication simulators that reproduce stale reads, LWW data loss, quorum behavior |
| 06 | [Partitioning](notebooks/part1-data-systems/06-partitioning.ipynb) | Key-range vs hash partitioning, skew, rebalancing, secondary indexes, routing | Consistent-hash ring with virtual nodes; hot-key mitigation; scatter-gather queries |
| 07 | [Transactions](notebooks/part1-data-systems/07-transactions.ipynb) | ACID precisely; isolation anomalies; MVCC, 2PL, SSI | A mini MVCC store that first exhibits, then prevents, each anomaly |
| 08 | [Distributed troubles](notebooks/part1-data-systems/08-distributed-troubles.ipynb) | Partial failure, timeouts, clock skew, process pauses, fencing | Failure-detection and split-brain sims; a clock-skew data-loss bug and its fix |
| 09 | [Consistency & consensus](notebooks/part1-data-systems/09-consistency-consensus.ipynb) | Linearizability, CAP, Lamport/vector clocks, total order broadcast, Raft | Vector clocks, a linearizability checker, and a toy Raft election + log replication |
| 10 | [Batch processing](notebooks/part1-data-systems/10-batch-processing.ipynb) | Unix philosophy, MapReduce, shuffle, joins, dataflow engines | A mini-MapReduce with partition/shuffle/sort running real jobs |
| 11 | [Stream processing](notebooks/part1-data-systems/11-stream-processing.ipynb) | Logs vs brokers, consumer groups, delivery semantics, windows, watermarks | A mini partitioned log broker; windowed aggregation with late events |
| 12 | [Derived data](notebooks/part1-data-systems/12-derived-data.ipynb) | Unbundling the database, lambda/kappa, integrity vs timeliness | An "unbundled database": one log feeding an index, a cache, and analytics |

### Part 2 — Machine Learning Systems (DMLS)
| # | Notebook | You learn | You build |
|---|----------|-----------|-----------|
| 13 | [ML systems overview](notebooks/part2-ml-systems/13-ml-systems-overview.ipynb) | ML in production vs research; when (not) to use ML; problem framing; objectives | One product problem framed three ways; cost-sensitive threshold optimization |
| 14 | [Data engineering for ML](notebooks/part2-ml-systems/14-data-engineering-for-ml.ipynb) | Formats (row vs column), lakes/warehouses, ETL/ELT, batch vs streaming | A mini ETL pipeline to partitioned Parquet; format benchmarks; a streaming ingester |
| 15 | [Training data](notebooks/part2-ml-systems/15-training-data.ipynb) | Sampling, labeling, weak supervision, active learning, class imbalance | Reservoir sampler; labeling functions + label model; the accuracy trap, fixed |
| 16 | [Feature engineering](notebooks/part2-ml-systems/16-feature-engineering.ipynb) | Missing data, scaling, encodings, hashing trick, crossing, **leakage**, feature stores | Three leakage bugs injected and detected; a train/serve-skew demo |
| 17 | [Model development & evaluation](notebooks/part2-ml-systems/17-model-dev-evaluation.ipynb) | Baselines-first, ensembles, experiment tracking; calibration, slice-based evaluation | A baseline ladder on a home-built experiment tracker; slice analysis |
| 18 | [Deployment & serving](notebooks/part2-ml-systems/18-deployment-serving.ipynb) | Batch vs online prediction, model compression, serving infrastructure | A tiny model server; dynamic batching experiment; INT8 quantization trade-offs |
| 19 | [Shifts & monitoring](notebooks/part2-ml-systems/19-shifts-monitoring.ipynb) | Covariate/label/concept shift, feedback loops, drift detection, ML observability | Drift detectors (KS, PSI, classifier); a degenerate feedback-loop simulation |
| 20 | [Continual learning & testing in production](notebooks/part2-ml-systems/20-continual-learning-testing.ipynb) | Retraining strategies and triggers; shadow, A/B, canary, bandits | Monitor-triggered retraining; an A/B simulator with the peeking problem; bandits |
| 21 | [Infrastructure & MLOps](notebooks/part2-ml-systems/21-infra-mlops.ipynb) | Infra layers, orchestrators, feature/model stores, build vs buy, teams | A mini DAG orchestrator running the full ML pipeline; a model registry |

### Part 3 — Capstones
| # | Notebook | What it exercises |
|---|----------|-------------------|
| 22 | [URL shortener + rate limiter](notebooks/part3-capstones/22-capstone-url-shortener.ipynb) | Requirements → estimation → ID generation → caching → rate limiting, load-tested |
| 23 | [News feed](notebooks/part3-capstones/23-capstone-news-feed.ipynb) | Fan-out on write vs read, the celebrity problem, caching layers |
| 24 | [Recommender system](notebooks/part3-capstones/24-capstone-recommender.ipynb) | Both books end to end: event log → features → candidates → ranking → serving → monitoring |
| 25 | [Fraud detection](notebooks/part3-capstones/25-capstone-fraud-detection.ipynb) | Real-time ML: point-in-time features, imbalance, low-latency serving, fallbacks |

## Setup

Requires [conda](https://docs.conda.io) (miniconda is fine).

```bash
make env    # create the "sysdes" conda env and install the helper package
make lab    # launch JupyterLab
```

If `conda` is not on your PATH: `make CONDA=~/miniconda3/condabin/conda env`.

## Testing

Every notebook is executable end to end and self-verifying (inline asserts).

```bash
make test-fast   # unit tests for the sysdes helper package (seconds)
make test        # + execute every notebook end to end (minutes)
make strip       # clear all notebook outputs (do this before committing)
```

## How to take the course

- **Full course**: 00 → 25 in order. Each notebook lists its prerequisites.
- **Data systems track**: 00–12 (+ capstones 22–23).
- **ML systems track**: 00–01, 13–21 (+ capstones 24–25). Notebooks 03, 11, 12 are useful background.
- Work the exercises before reading the solutions — that's where the learning is.

Notebooks write their scratch data (SSTable files, Parquet partitions, ...) under `~/tmp/sysdes-course/`,
never into the repo.

## Repository structure

```
notebooks/    the course (4 parts, 26 notebooks)
sysdes/       shared helpers: diagram drawing (viz) + discrete-event simulation (sim)
tests/        unit tests for sysdes + an execution test for every notebook
docs/         course design document (structure, conventions, dependency map)
```

See [docs/course-design.md](docs/course-design.md) for the design of the course itself.

## Books

This course is a companion to — not a replacement for — the books. Buy them, read them:

- Martin Kleppmann, *Designing Data-Intensive Applications*, O'Reilly, 2017.
- Chip Huyen, *Designing Machine Learning Systems*, O'Reilly, 2022.

All text, code, and diagrams here are original; each notebook ends with a mapping to the
relevant book chapters for deeper reading.
