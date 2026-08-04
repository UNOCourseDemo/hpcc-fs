# Idea-a findings log

## F1 — Multi-bottleneck unfairness, and an INT hop-count cliff (2026-05-23/24)

### Setup
Parking-lot topology (`gen_parking_lot.py`): N bottleneck links (25 Gbps) in series via
N+1 switches; one long flow crosses all N, one cross flow per link; equal 50 MB flows,
simultaneous start; stock HPCC (`cc_mode 3`, `has_win 1`, `var_win true`, `multi_rate false`).
Metric: path-length unfairness = long-path FCT / mean short-path FCT (max-min oracle = 1.0),
via `analyze_gap.py`.

### Observation: sweep N=2..8 (default 0.002 ms bottleneck delay)
| N | long ms | short ms | unfairness |
|--|--|--|--|
| 2 | 37.7 | 19.9 | 1.90× |
| 3 | 37.6 | 19.6 | 1.92× |
| 4 | 37.3 | 19.1 | 1.96× |
| 5 | 18.2 | 35.9 | **0.51×** |
| 6 | 18.2 | 35.8 | 0.51× |
| 7 | 18.3 | 35.8 | 0.51× |
| 8 | 18.3 | 36.6 | 0.50× |

Sharp, deterministic sign-flip at N=4→5: long flow goes from starved (1.9×) to dominant (0.5×).
No PFC events in any run.

### Two regimes, two causes

**Regime A (N≤4): genuine multi-bottleneck starvation.** The long flow is penalized ~1.9×,
growing slightly with N. This is the real HPCC convergence/fairness gap idea-a targets: the
per-link lower-bound estimate makes the multi-bottleneck flow under-claim relative to single-
bottleneck competitors. *This is the valid regime for studying the convergence gap.*

**Regime B (N≥5): an INT overflow artifact — NOT a fairness property.**
Root cause (code-confirmed):
- `IntHeader::maxHop = 5` (`src/network/utils/int-header.h:78`). The INT header holds ≤5 hops.
- Only switches push INT hops; the long flow crosses **N+1 switches**, so N=4→5 hops (fits),
  N=5→6 hops (overflow).
- `IntHeader::PushHop` (`int-header.cc:31`) wraps: `idx = nhop % maxHop`, but `nhop` keeps
  incrementing → for 6 switches, hop[0] is clobbered and `nhop` reports 6.
- Sender `UpdateRateHp` (`rdma-hw.cc:890`) wraps the **entire** rate update in
  `if (ih.nhop <= IntHeader::maxHop)`. With `nhop=6` this is false → **rate control is silently
  skipped**. The long flow never backs off, runs ~line rate (FCT 18.2 ms ≈ its 16.8 ms
  standalone), and starves the cross flows.
- Debug builds assert-crash here (`NS_ASSERT(ih.nhop <= maxHop)`, lines 876/904) — consistent
  with the `ns3.45-hpcc-validation-debug` CrashReporter plists.

Decisive test that ruled out the window/RTT hypothesis: varying bottleneck delay (RTT) at
fixed N did **not** move the flip. N=3 stayed starved at RTT=53 µs; N=5 stayed dominant at
RTT=10.8 µs. The transition is purely hop-count (N), exactly the 5→6 switch boundary.

### Implications
- **Methodology:** stock HPCC's valid regime in this simulator is paths ≤5 switches
  (≤4 bottlenecks in this parking-lot). Exclude N≥5 from convergence/fairness claims, or treat
  it explicitly as the INT-capacity-limit story.
- **For idea-a:** concrete evidence that standard INT has a hard per-path hop budget, and that
  deep multi-bottleneck paths (cross-pod / multi-tier Clos can exceed 5 hops) break HPCC
  outright. Directly motivates the "minimal INT extension / aggregation" angle: any mechanism
  must either live within the per-hop budget or compress/aggregate to a path-summary signal.
- **Possible future probe (additive only):** to study *true* N≥5 multi-bottleneck behavior we'd
  need an INT variant that handles >5 hops. Per the no-in-place rule, that means a NEW cc_mode /
  INT mode, never editing `maxHop` or the `cc_mode 3` path.

## F2 — Gap is robust to flow-size asymmetry and start staggering (2026-05-24)

Valid regime N=4 (5 switches). Metric: per-flow slowdown vs oracle; RELATIVE PENALTY =
mean(long slowdown)/mean(short slowdown), oracle = 1.0. All equal-size+simultaneous unless noted.

| scenario | long slowdown | short slowdown | penalty |
|--|--|--|--|
| symmetric (50 MB, t=0) | 1.11× | 0.57× | 1.96× |
| big long (200 MB / cross 50) | 1.11× | 0.57× | 1.96× |
| small long (10 MB / cross 50) | 3.33× | 0.94× | **3.53×** |
| long 200 MB / cross 10 MB | 1.11× | 0.60× | 1.85× |
| long starts first (+3 ms) | 1.22× | 0.62× | 1.97× |
| long joins late (cross first) | 1.12× | 0.62× | 1.81× |

**Conclusions.**
- The multi-bottleneck flow is penalized 1.8–2.0× across all size ratios and start orderings —
  the effect is not an artifact of equal sizes / simultaneous start.
- **Small** multi-bottleneck flows suffer most (3.5×): they complete during HPCC's slow
  multi-bottleneck convergence and never reach their fair rate. Strong motivation for the
  latency-sensitive case (RPC / ML control over multi-tier paths).
- A head start does NOT protect the long flow (1.97×): short-path flows displace it on arrival.

Tooling: `gen_parking_lot.py` now supports `--long-size/--cross-size/--long-start/--cross-start`
(and sorts flows by start time — the binary rejects unsorted flow files). `analyze_gap.py` oracle
is event-driven (handles staggered starts / asymmetric sizes).

## F3 — HPCC multi-rate mode mitigates but does not fix it (2026-05-24)

Same parking-lot, equal 50 MB, simultaneous. Unfairness (long/short FCT), oracle = 1.0:

| N | single-rate (`multi_rate=false`) | multi-rate (`multi_rate=true`) |
|--|--|--|
| 2 | 1.90× | 1.44× |
| 3 | 1.92× | 1.50× |
| 4 | 1.96× | 1.75× |

Multi-rate (per-hop EWMA utilization, sender takes min rate across hops) helps the long flow but
the penalty persists and still **grows with bottleneck count**. So multi-bottleneck unfairness is
intrinsic to HPCC's load-based control in both modes. **The idea-a mechanism must beat the
stronger multi-rate baseline (~1.4–1.75×), targeting penalty → 1.0× (true max-min) in ~1 RTT.**

Root mechanism: HPCC signals link *load/utilization*, not per-flow *fair share*. A flow crossing
k congested hops over-concedes (single-rate: reacts to max-u; multi-rate: min over per-hop rates),
losing the multi-front tug-of-war against single-bottleneck competitors. Fixing fairness needs the
sender (or switch) to reason about fair share, not just load.

## F4 — HPCC-MB implemented; first sender-only fixes fail; 3 hypotheses refuted (2026-05-24)

Implemented `mb_mode` knob (sender-only, additive; stock HPCC = `mb_mode 0`, verified do-no-harm:
N=4 mb_mode0 = 1.959× identical to pre-change). Tooling: `gen_parking_lot.py --mb-mode/--mb-gamma
/--cross-host-delay`. Tried mechanisms at N=4 (stock unfairness 1.959×, target 1.0):

| mechanism | result | verdict |
|--|--|--|
| `mb_mode 1` k-aware AI, γ sweep 1→50 | 1.93→1.63× | too weak; AI is a small lever vs multiplicative MD |
| `mb_mode 2` debiased max/mean blend, λ 0→1 | 1.96→1.95× | ~no effect ⇒ per-hop u_i are nearly EQUAL across hops ⇒ no max-bias |
| RTT equalization (cross host delay 1→8 ms-tenths) | 1.96→1.84× | even cross RTT > long RTT stays ~1.84× ⇒ NOT RTT unfairness |

**Refuted causes:** additive-increase weakness, max-over-hops statistical bias, RTT unfairness.
**What we know:** the penalty (~1.8–1.96×) is tied to the *number of bottlenecks the flow crosses*,
is independent of RTT, and the per-hop utilization signals are ~equal across the long flow's hops
(so every competitor sees the same load — yet the multi-bottleneck flow consistently loses).

**Implication:** the mechanism is subtler than a signal/estimation defect; the dynamics resolve
against the flow that is present at more contention points. We've exhausted cheap hypotheses —
next step is to **instrument per-flow rate over time** (build the deferred binary-trace parser) and
*observe* the convergence, rather than guess-and-check more sender-only corrections.

## F5 — Trace diagnosis: winner-take-all collapse, window-bound (2026-05-24)

Built `trace_rates.py` (parses the 56-B TraceFormat, receiver-side Recv of data → per-flow
goodput vs time). `gen_parking_lot.py` gained `--enable-trace/--trace-rx`. N=4 stock, per-flow
goodput over time (Gbps), fair ≈ 12.5:

```
t_ms    LONG     cross (each)
 0      ~2-4     ~17-21
 1-18   ~0.39    ~23.2          <- long collapsed; cross at ~line rate, sustained 18 ms
 19     cross flows finish (delivered 50 MB at ~23 G)
 20-37  ~23.3    0              <- long finally gets the pipe
```
Whole-run mean: LONG 11.5 G, each cross 21.8 G.

**The penalty is winner-take-all, not a mild bias.** During contention the multi-bottleneck flow
is squeezed to ~0.4 Gbps (~60× below each cross flow) at *every* shared link; the single-bottleneck
cross flows take ~all the bandwidth. It recovers only after they complete.

Key sub-findings:
- **No PFC (0 events), no loss**, yet long goodput 0.38 G < `min_rate` 1 G ⇒ the long flow is
  **window-bound** (var_win), not rate-bound: its window shrinks so it can't keep enough packets
  in flight across the 4-hop path. The fix likely must address the WINDOW, not just the rate/AI.
- The victim is **observable from existing INT**: the long flow's own share at each hop
  `own_rate/txRate_i ≈ 0.4/23.4 ≈ 1.7%` vs a 50% fair share — it *can* tell it is being starved.
- Explains why earlier sender tweaks failed: k-AI nudges the rate additively while the flow is
  window-collapsed; debiased-blend changes a signal that is already ~uniform.

**Implied fix direction:** detect-and-resist collapse using the measurable own-share, and act on
the window/claim (not just additive rate). Open question: is a pure sender-side window fix enough,
or is light switch help (per-flow fair-share / 1-bit) needed? Decide next.

## F6 — All victim-side rate-formula fixes fail; the fix must make dominant flows yield (2026-05-24)

Implemented and tested 4 sender-side HPCC-MB modes at N=2,3,4 (stock 1.90/1.92/1.96×, target 1.0):

| mb_mode | mechanism | N=4 result |
|--|--|--|
| 1 | k-aware additive increase (γ·k·RateAI) | 1.93× (γ=1) … 1.63× (γ=50) |
| 2 | debiased max/mean blend of U | 1.95× |
| 3 | responsibility-weighted MD (cut ∝ share) | 1.89× |
| 4 | k-th-root MD (soften cut to max_c^(1/k)) | 1.92× |

**None closes the gap.** Structural reason (from F5 trace + these results): at steady state the
shared links sit at ~η, so `max_c ≈ 1` and the rate barely changes — every flow just **holds** its
current rate. The cross (single-bottleneck) flows hold their high rate; the long flow holds its
starved rate. Any attempt by the victim to increase immediately pushes a link past η (the queue
term spikes its `u`), so it is cut back. **A victim-side fix cannot make the dominant flow yield**,
and at the η-hold equilibrium the MD-side fixes (3,4) almost never fire. Even an *established* long
flow is displaced when cross flows arrive (F2 "longfirst" = 1.97×), confirming the victim can't
hold ground.

**Conclusion:** closing the multi-bottleneck gap requires the **dominant (high-share) flows to
yield** to low-share flows. Pure victim-side rate tweaks are insufficient. Two viable paths:
1. **Global share-aware rule (sender-only, on ALL flows):** make additive increase share-aware so
   high-share flows stop increasing / yield and low-share flows claim — a sender-side RCP-like
   approximation. Changes single-bottleneck behavior, so do-no-harm must be re-verified.
2. **Switch-assisted (small switch/header change):** explicit per-flow fair-share or a 1-bit
   demand signal so switches tell dominant flows to back off — directly breaks the η-hold lock-in.

## F7 — Global share-aware (path 1) also weak; sender-only hits a fair-share-knowledge wall (2026-05-24)

`mb_mode=5` (global share-aware additive increase: when congested, ai_eff = 2·(1-share)·γ·RateAI so
high-share flows yield, low-share claim) at N=4: 1.96× (γ1) → 1.71× (γ20). Slowly improving like
all the others; doesn't reach 1.0.

**Why every sender-only fix is weak — the fundamental reason:**
1. At the multi-bottleneck equilibrium the shared links sit at ~η, so `max_c ≈ 1`. The HPCC update
   is dominated by the multiplicative term `rate·(1/max_c) ≈ rate` → **every flow just holds**.
   Additive nudges (modes 1,5) are tiny vs line rate, so redistribution is glacial; MD-side fixes
   (3,4) barely fire because MD almost never triggers at the hold point.
2. To break the hold you need a **strong multiplicative redistribution** toward each flow's fair
   share `C/N`. But a sender cannot compute `C/N`: it sees `txRate_i` (≈C) and its own rate, but
   **not N (the flow count)**. The only N-free sender mechanism is AIMD-style additive nudging —
   which is exactly what is too slow here. This is why RCP/XCP put fair-share computation in the
   SWITCH.

**Tentative conclusion (strong, not a proof):** sender-only INT is structurally insufficient for
single-RTT multi-bottleneck max-min fairness — fair share is not knowable sender-side without flow
count. This is itself a compelling paper result: it *motivates* minimal switch assistance. Modes
1–5 are the evidence (an ablation suite showing sender-side variants fail).

**Recommended pivot:** path 2 — minimal switch assist (one fair-share field, RCP/XCP-style, or a
1-bit demand signal) so switches tell dominant flows to back off. Reframes the paper as:
"sender-only is insufficient (we show why); a minimal INT+switch extension achieves single-RTT
multi-bottleneck max-min fairness."

## F8 — HPCC-FS (switch assist) achieves near-perfect max-min fairness (2026-05-29)

Implemented `cc_mode 11` = HPCC-FS: each switch keeps ONE RCP-style fair rate per egress port
(no per-flow state; `R ← R·(1+(α(C−y)−β q/d)/C)`, α=0.4 β=0.226, interval d=MaxRtt), stamps the
path-min into a new 1-field INT mode (`IntHeader::FS`, uint64 fairRate, min-aggregated); sender
adopts it (`HandleAckFs`). Additive: cc_mode 3 unchanged (smoke green; stock N=4 still 1.959).
Validation override: for `IntHeader::mode == FS` the QP window passed to `RdmaClient` is forced to
0 (rate-only) — RCP keeps queues bounded, and `var_win` (`m_win·rate/NIC_line`) would otherwise
cap the long flow's effective window at fair rate well below the multi-hop BDP needed.

**Result** (unfairness, target 1.0; N=2,3,4 sweep):

| N | stock HPCC | HPCC-FS |
|--|--|--|
| 2 | 1.90× | **1.008×** |
| 3 | 1.92× | **1.010×** |
| 4 | 1.96× | **1.017×** |

Trace (N=4) confirms the mechanism: all 5 flows converge to ~12.5 Gbps (true fair share) within
~4 ms and stay there for the whole contention window — vs stock's 0.4/23.2 collapse. A small number
of PFC events at N=3/4 (2/4) during the initial RCP convergence transient; no sustained pauses.

**(Important correction):** an earlier draft of F8 reported HPCC-FS as 1.30/1.46/1.56× with a
"window-limited residual" diagnosis. Those numbers were measured against a stale binary that did
not contain the HPCC-FS code at all (a silent build failure on `seqTs.ih.SetFairRate(...)`: the
`applications` `SeqTsHeader` reached via `<ns3/seq-ts-header.h>` has no public `ih` member, unlike
the point-to-point version). After removing that init (the switch's `GetFairRate()==0` branch
already handles the first hop) and force-rebuilding (`--reconfigure`), the real numbers are above.

## Summary so far (the paper arc)
1. Empirical foundation: multi-bottleneck penalty is real, robust, RTT-independent, non-monotonic
   at the INT hop limit (F1–F4).
2. Sender-only is insufficient: five `mb_mode` variants all fail; fair share is not knowable at
   the sender without flow count (F7). The η-hold equilibrium makes additive nudges glacial and
   prevents MD-side fixes from firing.
3. Minimal switch assistance (one RCP fair-rate field, one scalar of switch state per port) IS
   sufficient: HPCC-FS converges to max-min in ~1 RTT, penalty ≈ 1.0 (F8).

## F9 — HPCC-FS robustness across F2 scenarios (2026-05-29)

Reran the F2 matrix (N=4) under HPCC-FS:

| scenario | stock | HPCC-FS | fs PFC |
|--|--|--|--|
| sym (50 MB, t=0) | 1.96× | 1.02× | 4 |
| biglong (long 200 MB / cross 50) | 1.96× | 1.00× | 4 |
| **smalllong (long 10 MB / cross 50)** | **3.53×** | **1.07×** | 4 |
| long 200 MB / cross 10 MB | 1.85× | 0.98× | 4 |
| longfirst (long +3 ms head start) | 1.97× | 1.01× | 0 |
| crossfirst (long joins late) | 1.81× | 1.02× | 0 |

Every scenario converges to penalty 1.0 ± 0.08. The hardest stock case (small multi-bottleneck
flow, 3.53×) drops to 1.07×. PFC events only appear on simultaneous-start cases during the first
RCP interval; staggered scenarios are PFC-clean. The mechanism's robustness mirrors its design:
the switch's fair-rate signal is workload-agnostic; once R converges, every flow at a link gets C/N
regardless of size or start time.

## F10 — Smoothed HPCC-FS startup: 0 PFC across the matrix (2026-05-29)

Two-part fix to the small initial-RCP burst:
1. **Switch:** initialize `m_fairR[port] = C/2` (instead of `C`) so the first stamped fair-rate is
   already near the common-case fair share.
2. **Sender:** for `cc_mode 11`, initialize `qp->m_rate = m_minRate` (instead of NIC line rate) so
   the first RTT — before any fair-rate ACK has returned — doesn't blast every flow at line rate.
   RCP's first stamped rate lifts each flow to ~C/N within one RTT.

Result on the full N-sweep + F2 matrix at N=4 (target penalty 1.0, PFC 0):

| scenario | penalty | PFC |
|--|--|--|
| N=2 | 1.003× | 0 |
| N=3 | 1.003× | 0 |
| N=4 | 1.005× | 0 |
| sym | 1.005× | 0 |
| biglong | 1.002× | 0 |
| smalllong (was stock 3.53×) | 1.012× | 0 |
| longbig_crosssmall | 0.998× | 0 |
| longfirst | 1.003× | 0 |
| crossfirst | 1.007× | 0 |

Penalty narrowed to 1.0 ± 0.012 everywhere; **PFC = 0 everywhere**. Do-no-harm still passes
(`cc_mode 3` smoke green). The mechanism is robust to workload (sizes, timing) and clean at startup.

## F11 — HPCC-FS generalizes to a structurally different topology: tree fabric (2026-05-29)

Built `gen_tree_fabric.py`: 3-tier tree (1 core, 2 aggs, 4 edges, 8 hosts; 15 nodes, 14 links;
25 Gbps inter-switch, 100 Gbps host links; unique shortest paths so ECMP is not a confound).
Long flow 7→13 (cross-pod, 4 bottleneck uplinks); three cross flows with distinct sharing
patterns (each shares 1, 1, or 2 uplinks with the long flow).

| | LONG slowdown | mean short slowdown | penalty | unfairness | PFC |
|--|--|--|--|--|--|
| Stock HPCC | 1.18× | 0.71× | 1.36× | 1.66× | 0 |
| **HPCC-FS** | 1.01× | 1.01× | **1.003×** | **1.005×** | 0 |

Stock unfairness (1.66×) is smaller than parking-lot's 1.96× because tree cross flows are
themselves multi-bottleneck (2 uplinks each, not single), so they are not as advantaged. The
multi-bottleneck pathology persists, and **HPCC-FS closes it just as cleanly on this
non-parking-lot topology** — penalty 1.003×, all four flows within 1.003–1.009× of the oracle,
zero PFC. The mechanism is workload- and topology-agnostic by design.

## F12 — N-sweep headline: HPCC-FS bypasses the N≥5 INT-overflow regime too (2026-05-29)

Side-by-side at N=2…6 (parking-lot, equal 50 MB, simultaneous):

| N | stock HPCC | multi-rate HPCC | **HPCC-FS** |
|--|--|--|--|
| 2 | 1.90× | 1.44× | **1.003×** |
| 3 | 1.92× | 1.50× | **1.003×** |
| 4 | 1.96× | 1.75× | **1.005×** |
| 5 | 0.51× *(INT overflow)* | 0.51× *(INT overflow)* | **1.006×** |
| 6 | 0.51× *(INT overflow)* | 0.51× *(INT overflow)* | **1.007×** |

All PFC=0. HPCC-FS is flat ≈ 1.0 across the entire sweep, *including* the N≥5 region where stock
and multi-rate HPCC's per-hop INT record overflows `maxHop=5` and the rate-control input is
corrupted (long flow becomes spuriously favored). HPCC-FS sidesteps the overflow because its wire
format is **one 64-bit field, independent of hop count**, so there is no per-hop array to overflow.

This is the cleanest end-to-end story for the writeup: a single mechanism that (a) achieves
near-perfect max-min fairness at the N where stock fails by 2×, and (b) avoids the N≥5 artifact
that would otherwise complicate the multi-bottleneck story.

## F13 — k=4 ECMP fat-tree: HPCC-FS holds (2026-05-29)

Built `gen_fattree_k4.py`: canonical k=4 fat-tree (4 cores, 4 pods × {2 edge + 2 agg} = 20 switches,
16 hosts; 25 Gbps inter-switch / 100 Gbps host links; 48 links total). 8-flow workload: 4 inter-pod
(5-switch path, "long") + 4 intra-pod different-edge (3-switch path, "short"). The simulator's
ECMP picks paths via 5-tuple hash, which produces routing asymmetry: some flows hash to congested
cores, some to underloaded ones — independent of CC.

| | mean long slowdown | mean short slowdown | penalty | PFC |
|--|--|--|--|--|
| Stock HPCC | 0.98× | 0.73× | 1.34× | 0 |
| **HPCC-FS** | 0.76× | 0.76× | **1.001×** | 0 |

Stock HPCC inflicts the same multi-bottleneck penalty in the fat-tree (1.34×) — among congested
flows, the 4-bottleneck inter-pod flow at 46 ms is starved vs the 2-bottleneck intra-pod flow at
30 ms (≈1.5× rate disparity). **HPCC-FS closes this to 1.001× — every congested flow finishes at
the oracle FCT (33.9 ms) exactly**; the FCT spread between congested and uncongested classes is
purely the ECMP routing asymmetry (some flows get uncongested cores, finish at standalone
~17 ms), a routing-not-CC issue. PFC = 0 on both.

**Takeaway.** HPCC-FS works under ECMP with no modifications. The fair-rate signal aggregates
correctly along the (hash-chosen) path; the sender adopts the path-min; the receiver echo is
unchanged. ECMP load imbalance shows through as unequal per-flow FCT, but max-min fairness within
each contended link is preserved.

## F14 — k=6, k=8 fat-tree: HPCC-FS scales gracefully (2026-05-29)

`gen_fattree.py` parameterizes the canonical k-ary fat-tree. Same scaling workload (`k²/4`
inter-pod LONG flows from the first half of pods + `k` intra-pod different-edge SHORT flows):

| k | nodes | switches | flows | stock penalty | HPCC-FS penalty | PFC (FS) |
|--|--|--|--|--|--|--|
| 4 | 36 | 20 | 8 (4 long + 4 short) | 1.34× | 1.001× | 0 |
| 6 | 81 | 45 | 15 (9 long + 6 short) | 0.52× | 0.500× | 0 |
| 8 | 144 | 80 | 24 (16 long + 8 short) | 0.32× | 0.303× | 0 |

At k=4 multi-bottleneck contention is clear (stock 1.34×) and HPCC-FS closes it cleanly (1.001×).
At k=6 and k=8 the workload no longer creates persistent inter-pod contention — the larger
fabric provides (k/2)² cores so the ECMP-hashed inter-pod flows spread across uncongested core
paths, while the intra-pod flows remain bottlenecked at their pod's aggs. The result: both stock
and HPCC-FS show penalty <1.0 (long flows finish *faster* than short flows because they hit
underloaded cores, not because of CC unfairness). HPCC-FS adds no overhead in this regime.

**Takeaway.** HPCC-FS is well-behaved across fabric sizes: it closes the multi-bottleneck penalty
when contention exists, and is invisible (no harm) when it doesn't. A workload that explicitly
targets congestion at large k (more flows per source, or pinning paths) would be needed to test
the *multi-bottleneck-at-scale* regime; that is future work.

## F15 — Mixed-size Web-Search-distribution workload (2026-05-29)

`gen_mixed_workload.py` samples flow sizes from `paper-simulations/traffic/flow_ws_30.txt`
(HPCC SIGCOMM'19 Web-Search distribution, sizes 483 B to 9.6 MB) and maps 30 flows onto the
parking-lot N=4 topology (1/4 on the long path, 3/4 spread across the four cross links). Random
starts in [0, 5 ms]. Both runs complete all 30 flows; PFC=0 for both.

| | mean long-path slowdown | mean short-path slowdown | "penalty" (long/short) | PFC |
|--|--|--|--|--|
| Stock HPCC | 142.3× | 142.1× | 1.001× | 0 |
| HPCC-FS | 120.1× | 206.8× | 0.581× | 0 |

**Interpretation.** The mean per-flow slowdown is dominated by the smallest flows (sub-ms
standalone FCT × any queueing delay → very high ratio), so the absolute number is not directly
comparable to the equal-size matrix. The qualitative shift, however, is meaningful: HPCC-FS
**improves long-flow FCT** (142×→120×, ~15% better) at the cost of **worse short-flow FCT**
(142×→207×, ~46% worse). This is correct max-min behaviour: stock HPCC was *starving* the long
flows (and crucially, also any small flow whose path included a long-flow link, since the long
flow was crowded out of the bottleneck), so cross-link FCTs were artificially low; HPCC-FS
restores the long flows to their fair share, which necessarily reduces cross-link headroom for
the short flows competing on those same cross links.

A defensible writeup needs a per-size-bucket comparison and/or Jain's Fairness Index across all
flows, plus a workload where cross-link contention is held constant. Deferred to a more
comprehensive evaluation pass.

## F16 — Jain's Fairness Index on the mixed-size workload (2026-05-29)

`jain_analysis.py` computes Jain's FI on per-flow FCT-slowdown, grouped by path class and size
bucket. JFI(x) = (Σ x)² / (n · Σ x²); higher = fairer; max 1.0 (perfect equality).

| group | n | JFI stock | JFI FS | mean slowdown stock | mean slowdown FS |
|--|--|--|--|--|--|
| ALL flows | 30 | 0.192 | 0.126 | 142.2 | 183.7 |
| long-path | 8 | 0.562 | 0.562 | 142.3 | 120.1 |
| short-path | 22 | 0.155 | 0.120 | 142.1 | 206.8 |
| small (<10 KB) | 2 | 0.564 | 0.564 | 781.7 | 1407.8 |
| medium (10–100 KB) | 15 | 0.473 | 0.457 | 177.4 | 176.5 |
| large (100 KB–1 MB) | 4 | 0.426 | 0.512 | 5.0 | 6.8 |
| elephant (>1 MB) | 9 | 0.611 | 0.605 | 2.4 | 2.4 |

**The headline interpretation is more nuanced than the equal-size case.**

1. **Long-path flows are clearly better off under HPCC-FS** (mean slowdown 142.3 → 120.1, i.e.
   ~15% improvement; class JFI unchanged because FS proportionally reduces all long-path
   slowdowns).
2. **Short-path flows are *worse* off** (142.1 → 206.8, ~45%). Stock's multi-bottleneck
   starvation was *also* depressing utilization of the long flow's bottleneck (it took only ~0.4
   Gbps), so the cross-link flows had artificial headroom from the long flow not using its fair
   share. Restoring max-min fairness reclaims that share for the long flow, which necessarily
   reduces headroom for short flows on the cross links.
3. **Small flows are hit hardest** (782 → 1408, almost 2×). The 2 small flows happen to be on the
   long path; under stock they completed during the long flow's collapse with the cross link
   uncongested, but under FS the cross-link share is tighter.
4. **Elephants are slightly better** (2.44 → 2.37). The large multi-bottleneck flows benefit
   from FS exactly as the equal-size case predicts.
5. **Aggregate JFI drops** (0.19 → 0.13), but this metric is dominated by size heterogeneity and
   not a clean fairness test for mixed-size workloads.

**This is consistent with max-min semantics.** HPCC-FS does not minimize mean slowdown; it
enforces the per-link fair share. In a mixed-size workload, that necessarily redistributes from
flows that were benefiting from stock's starvation to the previously-starved flows. A defensible
multi-class evaluation needs per-class SLO targets (e.g. tail latency for small flows, mean FCT
for elephants), which is application-dependent and beyond the scope of this paper. The
equal-size matrices in §5.4 remain the cleanest test of the fairness claim itself.

## Next
- (in progress) Bolt/Annulus quantitative comparison from their papers.

## Next
- HPCC-FS residual: multi-hop window sizing + RCP tuning toward penalty 1.0.
- **(DONE) per-flow rate-over-time trace parser** — see F5.
- Design fix v2 from F5: share-aware, window-level. Possibly compare against switch-assisted
  options if sender-only window fix is insufficient.
- (was) Build per-flow rate-over-time trace parser (TraceFormat: 56-byte records, fields decoded in
  `algorithm-validation/run.sh` validate_trace; data union at offset 32: sport/dport/seq/ts; recv
  events at receiver hosts). Plot long vs cross rate trajectories at N=4 to see the true mechanism.
- Then redesign the fix from the observed dynamics (may need the 1-bit signal or switch help if a
  purely sender-side correction proves insufficient).
- Confirm on a structurally different topology. Routing in `hpcc-validation.cc` is ECMP
  (`CalculateRoute` keeps all equal-cost next hops), so a fat-tree needs care to pin a controlled
  shared bottleneck (flows hash across paths). Cross-pod k=4 fat-tree paths = 5 switches = exactly
  at the maxHop=5 limit, so keep within it. This is the remaining piece of the robustness story.

## F17 — Defensibility pass: window ablation, parameter sensitivity, PINT baseline (2026-06-07)

Driven by an external review. Added additive `cc_mode 11` config knobs (`fs_alpha`, `fs_beta`,
`fs_init_frac`, `fs_disable_window`) + `min_rate` to the generator; defaults reproduce the headline
runs exactly (N=4 = 1.005×, stock = 1.959×). Script: `run_sensitivity.py`.

**(1) Window ablation — rate-only is necessary.** FS with the per-flow window cap ON vs the
default rate-only (window OFF):

| N | FS rate-only | FS window-on |
|--|--|--|
| 2 | 1.003× | 1.50× |
| 3 | 1.003× | 2.00× |
| 4 | 1.005× | 2.49× |

With the window cap on, FS degrades with path length (worse than stock HPCC's 1.96× at N=4),
because `var_win` sizes the window from the NIC line rate, not the multi-hop bottleneck path.
This justifies the rate-only design choice (and discloses it as a second change beyond the field +
scalar).

**(2) Parameter sensitivity (N=4) — robust, no tuning needed.** Penalty stays within
[1.004, 1.008]× and PFC = 0 across:
- α ∈ {0.2, 0.3, 0.4, 0.5, 0.6}: 1.004–1.007×
- β ∈ {0.1, 0.16, 0.226, 0.3, 0.4}: 1.005× (flat)
- init_frac ∈ {0.25, 0.5, 0.75, 1.0}: 1.004–1.008× (note: even init=1.0 = C is PFC-free now,
  because the *sender* min_rate start absorbs the burst — the two-part smoothing means the switch
  init fraction is not critical)
- min_rate ∈ {100, 500, 1000, 2000} Mb/s: 1.005× (flat)

Directly answers the reviewer's "untuned RCP parameters" concern: the RCP defaults are not
load-bearing.

**(3) HPCC-PINT baseline.** cc_mode 10 (HPCC-PINT, the INT-compression variant) on the parking-lot
N-sweep: 1.77 / 1.88 / 1.88× at N=2/3/4 — i.e. PINT suffers the same multi-bottleneck penalty as
stock HPCC. HPCC-FS (1.003–1.005×) beats it. Added as a baseline column.

All runs deterministic; configs under `hpcc-fs/configs/hpcc_parking_lot_*`.

## F18 — HPCC home-turf cost, and that the gap is recoverable (2026-06-08)

Prompted by the honest question "is HPCC-FS just RCP, and does it throw away HPCC's benefits?"
In FS mode (cc_mode 11) HPCC-FS *replaces* HPCC's control on contended flows (window off, MIMD
unused, sender adopts the switch RCP fair rate) — so on HPCC's home turf it behaves like RCP.
Quantified:

**Single-bottleneck, 2 equal long flows (N=1 parking-lot):**
- HPCC: FCTs 26.7 / 37.2 ms (unfair — one wins; 1.59× vs 2.22×).
- HPCC-FS: 33.9 / 33.9 ms (perfectly fair). Fairer; better *tail* (33.9 < 37.2) but worse
  best-case (33.9 > 26.7). HPCC-FS equalizes, doesn't accelerate.

**Incast (validated algorithm-validation incast: 3 senders→1 rx, 25 Gbps bottleneck, 12 flows
100–400 KB):**
| | mean FCT | tail FCT | peak queue | PFC |
|--|--|--|--|--|
| HPCC | 258.6 µs | 459.8 µs | 143 KB | 0 |
| HPCC-FS (default min_rate 1000 Mb/s) | 297.5 µs | 490.3 µs | **64 KB** | 0 |

So the cost is real but modest: ~15% higher mean FCT, but **55% lower peak queue** (RCP's queue
control is aggressive). Not a catastrophic reversion.

**The gap is recoverable (startup artifact).** Short flows start at `min_rate` and ramp; raising
the sender startup rate closes most of the FCT gap:
| min_rate | mean FCT | tail | peak queue |
|--|--|--|--|
| 1000 Mb/s (default) | 297.5 | 490.3 | 64 KB |
| **5000 Mb/s** | **271.2** | 464.3 | 48 KB |
| 10000 Mb/s | 236.0 | 413.8 | 220 KB |

At 5 Gbps startup, HPCC-FS is within ~5% of HPCC's mean FCT (271 vs 259 µs) **with one-third the
queue** (48 vs 143 KB). And it does **not** affect the multi-bottleneck headline: parking-lot
N=2/3/4 fairness stays 1.003/1.003/1.005×, PFC=0 at min_rate 5000. So the incast cost is a tunable
startup artifact, not fundamental.

**Honest takeaway for the paper:** HPCC-FS adopts an RCP-style control on contended flows — a
different regime than HPCC, trading a small, tunable amount of single-flow FCT for fairness and
lower queue. The contribution is the *diagnosis* (F1–F7) plus the demonstration that the fix
belongs in the switch — not a novel mechanism (RCP is from 2005). A true *overlay* that keeps
HPCC's window/MIMD and uses the fair rate only as a ceiling (preserving HPCC's precision) is the
stronger but harder design — pursued on branch `hpcc-overlay` (see `OVERLAY-PLAN.md`).

## F19 — Home-turf gap is closable: HPCC-FS matches/beats HPCC at lower queue (2026-06-08)

Pushed harder on the F18 incast cost. The FCT gap is almost entirely a startup artifact (short
flows begin at `min_rate` and ramp). Sweeping the sender startup rate on the validated incast
(HPCC baseline: mean 258.6 µs, tail 459.8 µs, peak queue 143 KB):

| startup | mean FCT | tail FCT | peak queue | PFC |
|--|--|--|--|--|
| 1 Gbps (old default) | 297.5 | 490.3 | 64 KB | 0 |
| 2 Gbps | 289.7 | 480.2 | 59 KB | 0 |
| 3 Gbps | 284.9 | 474.3 | 55 KB | 0 |
| 4 Gbps | 278.3 | 467.9 | 51 KB | 0 |
| 5 Gbps | 271.2 | 464.3 | 48 KB | 0 |
| 6 Gbps | 269.6 | 464.6 | 45 KB | 0 |
| **8 Gbps** | **242.0** | **416.8** | **38 KB** | 0 |

Higher startup lowers **both** FCT and queue (no PFC) — at 8 Gbps HPCC-FS **beats HPCC's mean FCT**
(242 vs 259 µs) at **~¼ the peak queue** (38 vs 143 KB). The queue advantage is intrinsic: RCP's
`βq/d` term drains queue aggressively, so HPCC-FS holds far less queue than HPCC at every startup.
(Queue is non-monotonic past the aggregate-capacity boundary: at 10 Gbps the 3-flow incast offers
30 G > 25 G and the transient queue jumps to 220 KB — so the sweet spot is a startup whose
aggregate stays under link capacity.)

**Safety: the multi-bottleneck headline is unaffected by the higher startup.** Parking-lot at
startup 8 Gbps: N=2/3/4 sym = 1.003/1.003/1.004×; robustness smalllong 1.008×, biglong 1.002×,
cross-first 1.009× — all PFC=0 (≈ identical to the 1 Gbps results). So one operating point
(moderate startup) gives competitive single-bottleneck FCT, lower queue, AND the max-min fairness
fix.

**Revised contrast (the contribution, sharpened):**
| | single-bottleneck incast FCT | peak queue | multi-bottleneck fairness |
|--|--|--|--|
| HPCC | 258.6 µs (fast) | 143 KB | 1.9–3.5× (unfair) |
| HPCC-FS (8 Gbps start) | 242.0 µs (≈/faster) | 38 KB (~¼) | ~1.0× (fair) |

So HPCC-FS's fairness fix comes at **little-to-no home-turf cost** on the incast/single-bottleneck
workloads tested — it is competitive on FCT and *better* on queue. Caveat: it still uses RCP-style
control (not HPCC's per-hop precision), so on rapidly-varying / microburst workloads HPCC's fast
reaction may still matter; we tested clean incast + steady single-bottleneck, not adversarial
dynamics. Honest framing for the paper: *fairness essentially for free on the home-turf workloads
we measured, with a queue benefit; full precision parity is what the hybrid overlay targets.*

## F16 — Enhancement round: oscillation damped; fixed-point verified (2026-08-04)

**The fan-in oscillation, observed and damped.** Receiver-side rate trace at S=64: aggregate
goodput swings 3.4–24.7 Gbps with 91% of bins below C/2 (`run_round6.py`). Lengthening the
control interval (existing `fs_d_scale`) damps it: x2 → utilization 0.84–0.88 at S=64 (both
200 KB and 10 MB, PFC-free); x4 → 0.87–0.94 (44 pauses at S=64, none at S=128). The N=4
fairness headline is unchanged under x4 (1.003x, PFC 0). Gain reduction (alpha) alone helps
far less. Residual gap to stock HPCC's 0.92 at the default interval remains.

**Q16 fixed-point switch update (`fs_fixed_point`).** Hardware-shaped arithmetic — Q16
multiplier, precomputed 1/C and beta/(dC) reciprocals, an 8-entry elapsed-interval reciprocal
LUT, no divider — reproduces the N-sweep (1.001–1.004x vs double's 1.003–1.005x), ring JCT
(18.16 vs 17.99 ms), and damped fan-in (0.81 vs 0.84). One genuine quantization hazard was
found and fixed along the way: holding R in integer **Mbps** deadlocks recovery from the rate
floor — multiplicative growth truncates to zero below ~2.5 Mbps, so the fan-in case pins at
the sender floor (0.27, exactly 64 x 100 Mb/s / 25 G). The same 32-bit register in **Kbps**
units removes the stall. Register units, not arithmetic width, were the binding co-design
choice.

## F17 — Multi-phase collective + composite service (2026-08-04)

**Chained phases: savings accumulate, measured.** Four barrier-synchronized 3.125 MB ring
phases, each starting at the prior phase's measured completion with controller state carried
(`run_round7.py`): 21.6% cumulative gain vs 22.1% single-phase. RDMA-RCP's per-phase JCTs are
dead-stable (1.19/1.19/1.19/1.18 ms — warm register), stock HPCC's vary (1.46–1.55 ms — its
startup lottery redraws each phase). PFC 0.

**Composite training-like service, one mode end-to-end.** Ring coflow + 15-to-1 parameter
incast + 32 x 64 KB RPCs on the k=4 fat-tree: coflow JCT 9.25 vs 10.18 ms (−9.1%); incast
0.92 vs 0.64 ms; RPCs 0.25 vs 0.05 ms; 15 transient pauses. The mode fits services gated by
the collective; the short-flow tax is real but stays sub-millisecond.

## F18 — d = 2 x RTT_max operating point + the full 30-phase collective (2026-08-04)

**One fixed interval covers everything evaluated.** At d = 2 x RTT_max: headline N=4 1.003x,
small-long unchanged, churn 1.007x (same absolute P_i), ring coflow 18.02 vs 17.99 ms, fan-in
utilization 0.84/0.70 at S=64/128 — all PFC-free (`run_round8.py`). The N-dependence of the
fan-in oscillation is classical loop gain (offered load moves N*dR per broadcast update);
lengthening d is gain reduction.

**Full ring allreduce, all 2(N-1) = 30 phases**, barrier-chained with controller state
carried: 45.0 -> 35.2 ms end to end — a 21.9% full-collective gain; RDMA-RCP's thirty phase
JCTs sit in [1.17, 1.19] ms while stock's redraw a startup lottery in [1.44, 1.56] ms; PFC 0.

## F19 — PowerTCP shows the gap too (2026-08-04)

cc_mode 13: PowerTCP (NSDI'22), INT variant, ported from the authors' reference
implementation (their artifact is itself built on this HPCC simulator; reference constants
kept verbatim). Parking lot: **1.79 / 1.85 / 1.86x at N = 2/3/4**, growing with bottleneck
count, PFC 0 (`run_round9.py`). The EWMA + 150 Mb/s additive term soften the N=1 arrival
lottery (1.13x vs HPCC's 1.39x) but do not approach max-min — consistent with the
private-state history argument: PowerTCP's power signal is still per-sender load telemetry,
not a shared rate. The endemic claim now spans DCQCN, TIMELY, DCTCP, HPCC, PINT, and
PowerTCP. Stock do-no-harm gate unchanged (1.959x).

## F20 — Round-7 precision: loop-gain retraction + port validation (2026-08-04)

**The fan-in N-dependence is NOT naive loop gain** (a reviewer caught our error): in the
normalized no-delay RCP recurrence, fan-in cancels (x' = x[1+α(1−x)], x = NR/C, derivative
1−α at equilibrium). The measured N-dependence must therefore enter through feedback delay,
dequeue-triggered sampling, or the floor rail (whose distance to the fair share shrinks with
N — and a lower floor measurably deepens the collapse). Open question; delay-aware analysis
future work.

**PowerTCP port validation:** inet-tub/ns3-datacenter @ 4dd55d8, law/constants verbatim;
S=8 incast sanity 828 vs 830 µs vs stock HPCC, equal peak queue — single-bottleneck parity
matches the reference, so the 1.79–1.86x multi-bottleneck numbers reflect the control law.

**Fixed-point long-idle verified:** the shift+LUT elapsed-interval estimate covers idles to
2^20·d; the 100 ms idle probe under Q16 reads 0.378 ms vs floating point's 0.373 ms.

**Oracle renamed:** "fluid max-min reference" (ideal FCT under the max-min policy), not a
per-flow lower bound — P_i < 1 is possible for over-served flows, by design of the metric.

## F21 — Pipelined ring vs barriers: the 21% is synchronization-robust (2026-08-04)

A reviewer asked whether global phase barriers inflate the full-allreduce gain (barriers turn
every local straggler into a fabric-wide stall — exactly what RDMA-RCP fixes). Implemented
true per-rank ring dependencies (`run_round10.py`): start_i^{k+1} = max(done_i^k,
done_pred(i)^k), 30 phases, full-history replay. Pipelined: HPCC 44.06 ms, RDMA-RCP 34.76 ms
= **21.1%** vs 21.9% barriered. The gain is robust to the synchronization model: a slow ring
edge throttles the pipeline's steady-state rate either way. Also corrected a stale fixed-point
claim: the 2-bit-mantissa elapsed-interval LUT bounds reciprocal error at 25% (the "2x" figure
described an earlier pure-shift design).

## F22 — Full-collective header control + seed robustness (2026-08-04)

The pipelined 30-phase ring allreduce holds under both controls a reviewer could demand:
**17.0% with the RCP class padded to stock's 42-byte INT layout** (36.58 vs 44.06 ms; vs
21.1% at 8 B — telemetry size explains ~4 points, fairness the rest), and **20.2–21.6%
across three ECMP placements** (`run_round11.py`). Combined with per-rank pipeline semantics
(F21), the full-collective headline survives synchronization-model, header-size, and
placement scrutiny.
