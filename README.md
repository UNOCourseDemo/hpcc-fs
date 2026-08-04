# Multi-Bottleneck Fairness in RDMA Fabrics: Measurement and an Explicit-Rate Service Mode (RDMA-RCP)

An empirical study of multi-bottleneck max-min fairness on lossless RDMA fabrics, and
**RDMA-RCP** (implementation name `HPCC-FS`, `cc_mode 11`): an RCP service mode carried in *one*
INT fair-rate field with three words of mutable state per switch port, offered
alongside byte-for-byte unchanged stock HPCC. All of our work lives under `examples/hpcc/hpcc-fs/`.

**Finding 1 — the failure spans every scheme we evaluated.** On a parameterized parking-lot benchmark with a fluid
max-min oracle, *every* deployable RDMA CC scheme is unfair to the multi-bottleneck flow — DCQCN
**1.70–2.32×**, TIMELY 1.83–2.01×, DCTCP 1.61–1.78×, HPCC 1.90–1.96× at *N* = 2–4 — all growing
with bottleneck count and robust to start-time jitter
([`run_cc_baselines.py`](examples/hpcc/hpcc-fs/run_cc_baselines.py)). HPCC's instance is
**near-winner-take-all** (the long flow collapses to ~0.4 Gbps; 3.5× for small flows), RTT-independent,
and compounded past *N* = 4 by the original wire format's `maxHop = 5` cap.

**Finding 2 — where the rate state lives.** Six sender-only corrections fail — including a full
sender-side **mirror of the RCP recursion** driven by the same INT-visible inputs the switch would
use (`mb_mode 6`, [`run_vrcp.py`](examples/hpcc/hpcc-fs/run_vrcp.py)): 1.56× even with synchronized
starts, 1.65×/0.81× under staggered arrival (direction set by arrival order), while the identical
law at the switch holds ≈1.0×. **Per-flow fair queueing equalizes only what senders offer**
([`run_round4.py`](examples/hpcc/hpcc-fs/run_round4.py)): under the deployed windowed HPCC it
leaves 1.97× (the NIC-scaled window underfeeds the long flow); with the window removed DRR
equalizes (0.997×) — but at ~0.9 Gb/s per flow, **13.6× every flow's oracle FCT** (equal but
idle). Scheduling enforces *equality*; the max-min *allocation* — equal shares at full
utilization — also needs a rate signal telling each sender how much to offer. The mechanism is
history: private, independently maintained explicit-rate state preserves arrival-order
asymmetry; one shared per-link register erases it. Empirical evidence about explicit-rate state
placement, not a formal impossibility.

**Finding 3 — RDMA-RCP restores max-min.** Penalty **1.005× at *N* = 4** (flat through *N* = 6),
across asymmetric sizes / staggered + jittered starts / ECMP hash seeds — and across heterogeneous
capacities, unequal competitor counts, overlapping multi-bottleneck flows, and cross-flow churn
(generalized unfairness 1.001–1.007× with **every flow within 5–13% of its own oracle FCT** and
*higher* bottleneck utilization than stock,
[`run_stress_matrix.py`](examples/hpcc/hpcc-fs/run_stress_matrix.py), where stock reaches
1.41–2.87× with per-flow spread 0.41–1.34) — **zero PFC in every fairness experiment**, operating
rate-only *or* with a canonical RCP window (`cwnd = R·baseRTT`) — and cutting a ring-collective
coflow's JCT by **18–23%** at every seed tested (**18% with the INT header padded to stock's
42-byte layout** — the gain is fairness, not header thinness). On a **saturating k=6 fabric**
(108 inter-pod flows, 45 switches) makespan improves **14%** (−11% under a byte-identical
padded header; identical ECMP placements for both schemes) with zero PFC
([`run_round4.py`](examples/hpcc/hpcc-fs/run_round4.py)). Convergence is sub-millisecond and
path-length-independent; an idle port's frozen fair rate is benign after naturally draining
flows (the drain tail restores it to ≈C). **Fan-in and the rate floor:** conflating the
adopted-rate floor with the 1 Gb/s cold-start makes N ≤ C/1G a hard bound (at S=64 incast:
2,045 PFC pauses, 142 ms paused — floor-induced overload). With the floor decoupled
(`fs_min_rate`, default 100 Mb/s) the mode is **PFC-free through 128-way incast**, per-sender
rates reaching 182 Mb/s; the residual cost is ~2× stock HPCC's FCT at S≥64 — extreme fan-in
remains stock's home turf, now gracefully. Stock HPCC (`cc_mode 3`) is left **byte-for-byte
unchanged**.

**Deployment boundary (negative result).** The two modes do not share a link fairly — *even under
a weighted-DRR 50/50 reservation* (`dwrr_weights`), because both controllers still read
port-global telemetry: stock HPCC sees u≈1 from RCP traffic and never offers its reserved share
([`run_mixed_mode.py`](examples/hpcc/hpcc-fs/run_mixed_mode.py)). Per-class coexistence needs the
reservation to extend into the **telemetry** (per-class C, y, q — true slicing) or a separate
fabric. We report this rather than hide it.

**Defensibility evidence (paper §V):** a window ablation (the NIC-scaled window is the failure
mode — 1.5–2.5×; a fair-rate-scaled window `cwnd = R·RTT` matches rate-only at 1.004–1.006×),
parameter sensitivity (1.004–1.008× across α, β, startup, min-rate), and an HPCC-PINT baseline
(1.77–1.88× — a smaller INT footprint is *not* the fix; the field must carry a fair share).

> **📦 Artifact-review repository.** A self-contained, buildable snapshot of the HPCC-FS ns-3
> simulator.
> - **Paper:** [`examples/hpcc/hpcc-fs/paper.pdf`](examples/hpcc/hpcc-fs/paper.pdf)
> - **Slides:** [`examples/hpcc/hpcc-fs/talk/ipccc2026-talk.pdf`](examples/hpcc/hpcc-fs/talk/ipccc2026-talk.pdf)
> - **Project page:** <https://unocoursedemo.github.io/hpcc-fs/>
> - **Baseline reproduction** of the original HPCC (5 schemes × 2 workloads × 3 loads on a
>   376-node fat-tree): [`examples/hpcc/repro-verification/`](examples/hpcc/repro-verification/)
> - **Simulation results** (per-run `config.yml` + final outputs `fct`/`pfc`/`bottleneck`/`qlen`,
>   554 MB zstd, no per-run logs) — public archive on
>   [OneDrive](https://1drv.ms/f/c/6052297178cce52b/IgAsSQ7gNfdhQrNejod27CpkAYQs8xZs4QtGc_KKVWZjQLs?e=b0mS1t);
>   details in [`examples/hpcc/repro-verification/RESULTS.md`](examples/hpcc/repro-verification/RESULTS.md).

> **⚠️ This is the original HPCC simulator, modernized — not a re-implementation.** The original
> Alibaba HPCC simulator targets a much older ns-3. This repository upgrades that code base to a
> tagged modern release (**ns-3.45**) with **interface-level changes only** — build system,
> headers, deprecated-API replacements — while the **congestion-control logic, switch datapath,
> and wire formats are the original code** (one latent field-initialization bug, exposed only by
> the 376-node topology, is fixed and documented). The
> [reproduction](examples/hpcc/repro-verification/) confirms the upgraded code still matches the
> original paper's results, so measurements here are produced by the original implementation's
> logic. Because the upgrade is coherent across the tree, **the full tree is required to build**
> — it is not a drop-in patch set for the upstream repo.

---

## Where things live

All paper-project artifacts live under **`examples/hpcc/hpcc-fs/`**. Engine-level changes live in
`src/` and `examples/hpcc/`. The upstream ns-3 readme is preserved at `NS3-README.md`.

Throughout this document, **bare filenames refer to paths inside `examples/hpcc/hpcc-fs/`**; paths
beginning with `src/` or `examples/` are repo-root-relative.

**Reproducibility note.** The generated inputs (`configs/`, `flows/`, `topologies/`, `traces/`) and
`output/` are **gitignored**, not committed — they are reproduced deterministically from tracked
sources by the generators (`gen_*.py`) and the driver scripts (`run_sensitivity.py`,
`make_figures.py`). A fresh clone regenerates everything; nothing in the paper depends on a
committed config snapshot.

---

## Read the paper

| File | What it is |
|---|---|
| `paper.pdf` | Compiled 10-page paper (ACM `acmart` sigconf), ready to view |
| `paper.tex` + `paper.bib` | LaTeX sources |
| `paper-ipccc.pdf` + `paper-ipccc.tex` | IEEE-format submission version (IPCCC), same content |
| `talk/ipccc2026-talk.pptx` / `.pdf` | Conference talk slides (19 slides, speaker notes; the `.pptx` is authoritative) |
| `figures/*.png` | All paper figures (regenerated live by `make_figures.py`) |

**Build the PDF.** From `examples/hpcc/hpcc-fs/`:
```bash
pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper
```

---

## The story arc — one-line tour of `findings.md`

| # | Topic | Headline |
|--:|---|---|
| F1 | Multi-bottleneck penalty exists | Stock HPCC unfairness 1.90 / 1.92 / 1.96× at *N* = 2 / 3 / 4; INT overflow at *N* ≥ 5 |
| F2 | Robustness of the gap | Penalty 1.81–1.97× under asymmetric sizes/staggered starts; **3.53×** when long flow is small |
| F3 | HPCC multi-rate mode | Mitigates but doesn't fix: 1.44 / 1.50 / 1.75× |
| F4 | Not RTT unfairness | Equalizing cross-flow RTT (10× sweep) doesn't move the penalty |
| F5 | Trace diagnosis | Winner-take-all collapse: long flow at 0.4 Gbps, cross flows at 23 Gbps for 18 ms |
| F6 | HPCC-MB ablation scaffold | New `mb_mode` knob; `mb_mode 0` = stock HPCC, byte-identical |
| F7 | Five sender-only fixes fail | A sender cannot compute `C/N` without knowing the flow count `N` |
| F8 | HPCC-FS works | *N* = 4 penalty **1.005×**, all flows at fair share sub-ms |
| F9 | Robustness under HPCC-FS | Penalty within 1.0 ± 0.08 across all six F2 scenarios |
| F10 | Smoothed startup | **PFC = 0 everywhere** (two-part smoothing) |
| F11 | Tree fabric topology | Stock 1.36× → HPCC-FS **1.003×** |
| F12 | Extended *N*-sweep | HPCC-FS flat at ≈1.0× through *N* = 6 — bypasses the INT-overflow regime |
| F13 | *k* = 4 ECMP fat-tree | HPCC-FS **1.001×** (oracle-normalized), PFC = 0 |
| F14 | *k* = 6, 8 fat-tree | ECMP load placement dominates; HPCC-FS adds no overhead |
| F15 | Mixed-size workload (Web-Search) | Long flows 142→120× (better); short flows 142→207× (correct max-min trade-off) |
| F16 | Jain's Fairness Index | Per-class / per-size-bucket analysis confirms F15 |
| F17 | Defensibility pass | Window ablation, α/β/init/min-rate sensitivity (1.004–1.008×), HPCC-PINT baseline (1.8×) |

---

## Reproduce

**Headline result** (parking-lot *N* = 4):
```bash
# 1. Build the optimized binary (one-time, ~minutes)
cd <repo-root>                                   # the directory containing this README
bash examples/hpcc/algorithm-validation/run.sh --optimized --build-only

# 2-4. Generate config, run, analyze (expect "UNFAIRNESS ... = 1.005x", PFC = 0)
cd examples/hpcc
../../venv/bin/python hpcc-fs/gen_parking_lot.py --n 4 --cc-mode 11 --suffix _fs
mkdir -p hpcc-fs/output/parking_lot_4bn_fs
../../build/examples/hpcc/ns3.45-hpcc-validation-optimized \
    hpcc-fs/configs/hpcc_parking_lot_4bn_fs.yml > hpcc-fs/output/parking_lot_4bn_fs/sim.log
../../venv/bin/python hpcc-fs/analyze_gap.py hpcc-fs/configs/hpcc_parking_lot_4bn_fs.yml
grep -c . hpcc-fs/output/parking_lot_4bn_fs/pfc.txt   # → 0
```

**All figures (live, deterministic) and all defensibility experiments** — from the repo root:
```bash
venv/bin/python examples/hpcc/hpcc-fs/make_figures.py        # regenerates every paper figure from runs
venv/bin/python examples/hpcc/hpcc-fs/run_sensitivity.py     # window ablation + sensitivity + PINT baseline
```

---

## Engine changes (all additive — `cc_mode 3` untouched)

| Change | Files | What |
|---|---|---|
| **HPCC-FS** (`cc_mode 11`) | `src/network/utils/int-header.{h,cc}` | New INT mode `FS` carrying one `uint64 fairRate` field |
| | `src/point-to-point/model/switch-node.{h,cc}` | Per-port RCP fair-rate scalar (`m_fairR[port]`) — **one float per port, no per-flow state** |
| | `src/point-to-point/model/rdma-hw.{h,cc}` | New `HandleAckFs`: sender adopts path-min fair rate |
| | `examples/hpcc/hpcc-validation.cc` | Wire-up: `IntHeader::mode = FS` for cc_mode 11; rate-only (window off) in FS mode |
| | `examples/hpcc/hpcc-config.{cc,h}` | Config keys: `fs_alpha`, `fs_beta`, `fs_init_frac`, `fs_disable_window` |
| **HPCC-MB ablation** (`mb_mode 1–5`) | `src/point-to-point/model/rdma-hw.{cc,h}` | Five sender-side variants that fail: k-AI, debiased blend, responsibility-weighted MD, k-th-root MD, share-aware AI |
| | `examples/hpcc/hpcc-config.{cc,h}` | Config keys: `mb_mode`, `mb_gamma` |

Defaults of every new knob reproduce the headline runs exactly (verified: cc_mode 11 default = 1.005×,
cc_mode 3 = 1.959× at *N* = 4).

---

## Tools (Python) under `hpcc-fs/`

| Script | Purpose |
|---|---|
| `gen_parking_lot.py` | Parameterized parking-lot generator (`N`, sizes, starts, delays, `cc_mode`, `mb_mode`, `fs_*`, …) |
| `gen_tree_fabric.py` | 3-tier tree fabric (15 nodes, unique paths, no ECMP) |
| `gen_fattree.py` | k-ary fat-tree (any even `k`); `k = 4, 6, 8` in the evaluation |
| `gen_fattree_k4.py` | Original hand-built *k* = 4 fat-tree (predecessor of `gen_fattree.py`) |
| `gen_mixed_workload.py` | Sample flow sizes from HPCC's Web-Search distribution |
| `analyze_gap.py` | Max-min oracle (event-driven progressive filling) + unfairness/penalty metric |
| `trace_rates.py` | Parse binary `trace.tr`; per-flow goodput over time |
| `jain_analysis.py` | Jain's Fairness Index by path class / size bucket |
| `run_sensitivity.py` | Window ablation + parameter sensitivity + HPCC-PINT baseline (F17) |
| `make_figures.py` | Regenerate every paper figure **from live runs** (`--cache` to reuse outputs) |
| `make_topology_figures.py` | Draw the three topology diagrams |

---

## Other docs

- **`findings.md`** — chronological experiment log (F1 → F19) documenting the investigation behind
  the paper. The single most useful supporting document.

---

## Navigation cheat-sheet

| If you want to… | Start here |
|---|---|
| Read the paper | `paper.pdf` |
| Trace the research chronologically | `findings.md` (F1 → F19) |
| Understand the HPCC-FS mechanism | `paper.tex` §4 (incl. Algorithms 1–2) |
| Reproduce a result | *Reproduce* section above |
| Modify the engine | *Engine changes* table above |
| Run a custom workload | `gen_parking_lot.py --help`, `gen_fattree.py --help`, … |

---

## About this snapshot

This public repository is a clean, single-commit snapshot of the HPCC-FS paper branch, prepared for
artifact review. It contains everything needed to build the simulator and reproduce the paper's
results. Large generated artifacts (build outputs, packet traces, and the 3.5 GB raw FCT data) are
excluded and archived separately — see [`examples/hpcc/repro-verification/RESULTS.md`](examples/hpcc/repro-verification/RESULTS.md).
