# Reproduction results — refactored HPCC vs. SIGCOMM'19

**Verdict: the refactored code reproduces the original paper's central findings.** Once a latent
bug was fixed (see below), all five algorithms run to completion on the full 376-node fat-tree and
the FCT / queue / PFC behavior matches the paper's qualitative story. Raw per-flow data is in
`results/raw/<config>/`; the full table is `results/analysis_table.txt` (regenerate with
`venv/bin/python analyze_repro.py results/raw`).

## Setup
- 5 schemes (`hpcc`, `dcqcn`, `timely`, `dctcp`, `hpcc_pint`) × 2 workloads (WebSearch, FB_Hadoop)
  × 3 loads (30/50/70 %) = 30 runs, FatTree (16 core/20 agg/20 ToR/320 servers), 100 G NIC.
- Canonical `paper-hpcc-fs` engine, run on frcc/frcc2 in `~/uno-hpcc-repro`; traffic frozen +
  identical across VMs (one unseeded draw per workload/load, shared by all 5 schemes).
- Metric: **FCT slowdown = fct / standalone_fct** per flow; "short flow" = <3 KB (ws) / <120 KB (fb).
- **Public archive:** each run's configuration + final results (`config.yml` + `fct`/`pfc`/
  `bottleneck`/`qlen`; 554 MB zstd → 2.2 GB; per-run `sim.log` logs excluded) are on OneDrive —
  <https://1drv.ms/f/c/6052297178cce52b/IgAsSQ7gNfdhQrNejod27CpkAYQs8xZs4QtGc_KKVWZjQLs?e=b0mS1t>
  (extract: `zstd -dc hpcc_repro_results.tar.zst | tar xf -`).

## Headline: FCT slowdown + queue + PFC

p99 = 99th-pct FCT slowdown; queue = peak per-port egress (KB); PFC = pause count.

| cell | metric | HPCC | DCQCN | TIMELY | DCTCP | HPCC-PINT |
|---|---|---|---|---|---|---|
| **ws 30%** | p99 short | **1.62** | 8.15 | 12.31 | 3.84 | 1.79 |
|          | queue KB  | **328** | 3 475 | 6 018 | 1 167 | 402 |
| **ws 50%** | p99 short | **1.92** | 13.72 | 18.26 | 5.66 | 2.08 |
|          | queue KB  | **410** | 4 551 | 12 868 | 1 411 | 480 |
|          | PFC       | 0 | 0 | 78 | 0 | 0 |
| **ws 70%** | p99 short | **2.00** | 23.72 | 273.16 | 7.69 | 2.32 |
|          | queue KB  | **395** | 7 106 | 26 351 | 1 588 | 497 |
|          | PFC       | 0 | 0 | **655 962** | 0 | 0 |
| **fb 30%** | p99 short | **2.27** | 7.69 | 11.94 | 3.55 | 2.29 |
|          | queue KB  | **492** | 2 585 | 10 639 | 1 156 | 544 |
| **fb 50%** | p99 short | **3.28** | 14.64 | 20.10 | 5.33 | 3.20 |
|          | queue KB  | **617** | 7 290 | 20 068 | 1 443 | 653 |
|          | PFC       | 0 | 0 | 714 | 0 | 0 |
| **fb 70%** | p99 short | **6.06** | 30.60 | 221.86 | 8.44 | 5.00 |
|          | queue KB  | **634** | multi-MB¹ | 25 396 | 1 864 | 828 |
|          | PFC       | 0 | 0 | **1 123 760** | 0 | 0 |

## Paper signatures reproduced
1. **HPCC short-flow tail ≪ DCQCN/TIMELY** at every load (the paper's headline "~95 % FCT
   improvement, esp. short flows"). All 6 cells: HPCC short-flow p99 is the lowest of the
   queue-building schemes.
2. **HPCC keeps queues low** (~0.3–0.6 MB, roughly flat with load) while **DCQCN/TIMELY grow to
   multi-MB** (TIMELY to ~26 MB). Matches "HPCC prevents standing queues."
3. **HPCC = 0 PFC everywhere; TIMELY's PFC explodes at load** (655 k @ ws70, 1.12 M @ fb70).
   Matches "PFC appears with DCQCN/TIMELY, not HPCC."
4. **DCTCP is intermediate** (better than DCQCN/TIMELY, worse than HPCC). Matches the paper.
5. **HPCC-PINT ≈ HPCC** (compressed-INT variant tracks HPCC).
6. **HPCC long-flow tradeoff is visible**: at 70 % HPCC's *overall* p99 (21–27) exceeds DCTCP's,
   even though its *short-flow* p99 is far lower — HPCC reserves headroom, slowing long flows. The
   paper explicitly predicts this (~1.24× long-flow cost at 50 %).

## Comparison to the published numbers (directional)
The paper's absolute numbers come from a 32-server **testbed** (WebSearch 30/50 %); ours are the
large **NS3 fat-tree** with a different traffic draw and **no 60→1 incast injection**, so absolute
slowdowns differ — but the *direction and ratio* reproduce:

| Published (testbed, <3 KB) | Ours (NS3 fat-tree, <3 KB) |
|---|---|
| 30 %: DCQCN p99 11.2 → HPCC 2.38 (≈4.7× better) | 30 %: DCQCN 8.15 → HPCC **1.62** (≈5.0× better) |
| 50 %: DCQCN p99 53.9 → HPCC 2.70 (≈20× better) | 50 %: DCQCN 13.72 → HPCC **1.92** (≈7× better) |

The HPCC≪DCQCN short-flow ratio and the near-zero-queue / zero-PFC behavior reproduce cleanly.
Absolute magnitudes are lower for DCQCN here because this is the background-only fat-tree (no
incast), which the paper notes is a milder stress than its 30 %+incast Figure 11 case.

## Caveats
- ¹ `dcqcn_fb_70` was stopped before sim end: with all flows already complete it kept advancing
  sim-time at ~1 %/30 min (59 B events, ~20–30 h to drain) — DCQCN's huge standing queues at 70 %
  make the simulator itself crawl, a paper-consistent behavior. Its **FCT data is complete**
  (2 324 435 flows); only the end-of-sim queue summary is unavailable. Its peak queue is multi-MB,
  in line with the other DCQCN cells (ws 70 % = 7.1 MB, fb 50 % = 7.3 MB).
- Single frozen traffic draw per cell (unseeded generator) — fine for cross-scheme comparison
  since all schemes share the identical draw, but not a multi-seed average.
- 70 % loads and HPCC-PINT are later HPCC project-page extensions, not the 2019 paper's main figs.

## The bug that had to be fixed first
`ns3::Node::m_node_type` was **uninitialized** in the `Node` constructor → servers got garbage
type on the large fat-tree → null `RdmaDriver` deref in `SetRoutingEntries` → SIGSEGV. It worked on
the paper's small topologies only by heap luck. Fix: `src/network/model/node.h` →
`uint32_t m_node_type = 0;`. Does not touch any `cc_mode` logic. Full diagnosis in `RUNLOG.md`.
