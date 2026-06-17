# Reproduction Verification — refactored HPCC vs. original paper

**Goal.** Confirm that our **refactored / re-ported** HPCC simulator still reproduces the
qualitative results of the original HPCC paper (Li et al., SIGCOMM '19) and the later
HPCC project-page extensions, across **all** congestion-control algorithms — *before* we lean
on this codebase for the HPCC-FS follow-on. This is a regression/sanity gate, not a new result.

This folder is the **dedicated record** of that verification: the exact code, the exact (frozen)
traffic, the run harness, the raw outputs, and the side-by-side against published expectations.

## What is being verified

| Axis | Values |
|---|---|
| Schemes (`cc_mode`) | `hpcc` (3), `dcqcn` (1), `timely` (7), `dctcp` (8), `hpcc_pint` (10) |
| Workloads | `ws` (WebSearch), `fb` (FB_Hadoop) |
| Loads | `30`, `50`, `70` % |

= **30 configs** under `paper-simulations/configs/`. Topology = `mix/fat.txt`
(FatTree: 16 core / 20 agg / 20 ToR / 320 servers, 100 G NIC, 400 G fabric; 376 nodes).

## Code of record

- Branch `paper-hpcc-fs`, HEAD `e9e167f2d` (the 4 commits above `origin` are **paper text only**;
  the engine is unchanged since `c4c2c7a54`, which is on `origin`).
- The refactored algorithm code (`cc_mode` 1/3/7/8/10) is what we are validating. The HPCC-FS
  additions (`cc_mode 11`, FS INT mode, RCP switch block) are **additive** and not exercised here.
- The VMs' own `~/uno-hpcc` checkouts carry the user's separate `afs` (adaptive-fair-share)
  experiments and have **diverged** from canonical — so this campaign runs the canonical source in
  a **clean** dir `~/uno-hpcc-repro` on each VM, leaving the `afs` work untouched.

## Traffic is frozen (important)

`uno-hpcc/traffic_gen_uno/traffic_gen.py` uses `random.*` with **no seed** → traffic differs every
run. So we generate the 6 `flow_<wl>_<load>.txt` files **once**, freeze them, checksum them, and
ship the *identical* files to both VMs. All 5 schemes at a given (workload, load) therefore see the
same offered load — the only correct way to compare schemes. Checksums recorded in
[`traffic_checksums.txt`](traffic_checksums.txt).

## Execution plan (frcc + frcc2)

Each ns-3 run is single-threaded; each VM has 32 cores / 47 GB. So we run the 30 configs in
**parallel**, ~15 per VM (≈3 GB RAM headroom per sim), rather than serially.

- **frcc** (10.0.0.50): all `ws` configs + half `fb` — 15 runs
- **frcc2** (10.0.0.51): the other half — 15 runs

Steps (recorded in [`RUNLOG.md`](RUNLOG.md)):
1. `rsync` canonical source → `~/uno-hpcc-repro` on both VMs (excl. build/artifacts).
2. Build optimized binary on both: `cd ~/uno-hpcc-repro && bash examples/hpcc/paper-simulations/run.sh --optimized --build-only`.
3. Push the 6 frozen traffic files to both VMs.
4. Launch the per-VM config subsets in the background (`nohup`), one output dir per config.
5. Collect `fct.txt` / `pfc.txt` / `bottleneck.txt` / `qlen.txt` back into `results/`.
6. Analyze: FCT slowdown by flow-size bucket, queue tail, PFC. Compare to targets below.

## Published expectations to check against

(From `paper-simulations/ORIGINAL_PAPER_RESULTS_SUMMARY.md`; full nuance there.)

| Signal | HPCC | DCQCN / TIMELY |
|---|---|---|
| Short-flow tail FCT (<3 KB ws, <120 KB fb) | much lower | higher (standing queue) |
| Queue tail | median ≈ 0, tail ≪ MB | up to MB-scale |
| PFC | none / near-zero in background-only cases | appears mainly under 30%+incast stress |
| Long flows | slightly worse for HPCC (headroom + INT overhead) | can look better (fills buffers) |
| DCTCP | better than DCQCN/TIMELY in sim, but HPCC still ~2× lower latency | — |

**Caveats** (these are *not* original SIGCOMM'19 Figure 10/11 cases):
- No 60→1 incast injection here, so a clean `fb_30` background-only run may show **no PFC** for
  DCQCN — not a regression. The paper's PFC story is the 30%+incast case.
- `*_70` loads and `hpcc_pint_*` are later project-page extensions; compare to the key-results page.
- The correctness story is **not** "HPCC wins every metric" — it is: HPCC sharply lowers latency /
  short-flow tail FCT by preventing standing queues + PFC, accepting a controlled long-flow tradeoff.

## Layout

```
repro-verification/
  README.md                 ← this file
  RUNLOG.md                 ← timestamped commands + per-VM launch record
  traffic_checksums.txt     ← sha256 of the 6 frozen flow files
  results/                  ← collected fct/pfc/queue per config + the comparison table
```

The 3.5 GB of raw per-flow outputs is gitignored; the **public archive** (625 MB zstd) is on OneDrive:
<https://1drv.ms/f/c/6052297178cce52b/IgAsSQ7gNfdhQrNejod27CpkAYQs8xZs4QtGc_KKVWZjQLs?e=b0mS1t>
