# Original HPCC Paper Results Summary

This note summarizes the published results from the original HPCC SIGCOMM 2019 paper, not the results currently produced by this checkout. For local rerun output, see `PAPER_RESULTS_SUMMARY.md` and `paper_results_detailed.md`.

Sources checked:

- Local paper copy: `examples/hpcc/hpcc.pdf`
- Author-hosted paper PDF: <https://minlanyu.seas.harvard.edu/writeup/sigcomm19.pdf>
- HPCC project page: <https://hpcc-group.github.io/>
- HPCC later key-results page: <https://hpcc-group.github.io/results.html>
- Original Alibaba simulator repo: <https://github.com/alibaba-edu/High-Precision-Congestion-Control>

## What The Original Paper Evaluated

The paper evaluates HPCC against DCQCN, TIMELY, DCQCN with a sending window, TIMELY with a sending window, and DCTCP.

The paper has two main result environments:

| Environment | Setup | Workloads | Loads |
|---|---|---|---|
| Testbed | 32 servers, one aggregation switch, four ToRs, 25 Gbps server NICs, 100 Gbps switch links | WebSearch and FB_Hadoop | 30%, 50% |
| NS3 simulation | FatTree with 16 core switches, 20 aggregation switches, 20 ToRs, 320 servers, 100 Gbps server NICs, 400 Gbps fabric links, 32 MB switch buffers | Mainly FB_Hadoop in Figure 11, with WebSearch reported as similar | 30% plus incast, 50% |

The main metrics are FCT slowdown, flow bandwidth, network latency, PFC pause duration, and in-network queue size. The paper assumes 42 bytes of HPCC INT header overhead per data packet as a conservative worst case.

## Headline Results

HPCC's central result is that precise INT feedback lets it keep queues close to zero while still using bandwidth efficiently. The paper reports up to 95% FCT improvement versus DCQCN/TIMELY, especially for short flows and tail latency.

In the 32-server testbed under WebSearch:

| Case | Published result |
|---|---|
| 30% load, flows shorter than 3 KB | 99th-percentile FCT slowdown improved from 11.2 with DCQCN to 2.38 with HPCC. |
| 50% load, flows shorter than 3 KB | 99th-percentile FCT slowdown improved from 53.9 with DCQCN to 2.70 with HPCC, reported as a 95% reduction. |
| 50% load queue tail | HPCC p95/p99 queue sizes were 19.7 KB / 22.9 KB, while DCQCN was 1.1 MB / 2.1 MB. |
| PFC implication | HPCC queues stayed below the PFC threshold in those experiments, so PFC was not needed to protect losslessness. |

In the large-scale NS3 simulations:

| Case | Published result |
|---|---|
| FB_Hadoop 30% load plus incast | The paper adds 60-to-1 incast traffic, each sender sending 500 KB, adding about 2% network load. |
| FB_Hadoop 50% load | No extra incast is needed to stress the network. |
| Short-flow FCT | For flows shorter than 120 KB, HPCC has much lower 95th-percentile FCT slowdown than the alternatives. The paper notes that about 90% of FB_Hadoop flows are shorter than 120 KB. |
| Latency | HPCC keeps tail RTT under 20 microseconds; at 50% load, the 95th-percentile latency is 19.8 microseconds, less than 8 microseconds above the 12 microsecond base RTT. |
| PFC | Large-scale PFC pause time appears with DCQCN and TIMELY, not with HPCC. Adding a sending window to DCQCN/TIMELY almost eliminates PFC, which supports the paper's argument that controlling inflight bytes is key. |
| DCTCP comparison | DCTCP performs better than DCQCN/TIMELY in the paper's simulator-only comparison, but HPCC still reduces DCTCP latency by more than 2x. |

## Important Tradeoff

The paper explicitly calls out a long-flow tradeoff. HPCC reserves bandwidth headroom and carries INT metadata, so long flows can be slower than schemes that keep buffers full. At 50% load, the paper's residual-capacity calculation predicts HPCC long-flow FCT can be about 1.24x slower than other schemes. That is expected behavior, not automatically a bug, when short-flow latency is the priority.

## Design Checks Reported By The Paper

The paper also uses microbenchmarks to show the mechanism:

| Check | Expected HPCC behavior |
|---|---|
| Long-short flow | HPCC restores the long flow rate immediately after the short flow exits; DCQCN still has not returned to line rate after more than 2 ms. |
| Small incast | HPCC reacts after one RTT and drains the queue quickly; DCQCN builds about 550 KB of queue. |
| Elephant plus mice | HPCC keeps 1 KB mice-flow latency close to the 5.4 microsecond base RTT; DCQCN stays above 35 microseconds because of standing queue. |
| Fair-share | HPCC converges to good fairness as flows join and leave. |
| ACK reaction | Per-ACK reaction alone overreacts, per-RTT reaction alone reacts too slowly, and HPCC's reference-rate approach gets fast reaction without large oscillation. |

## What Is Not Original SIGCOMM 2019

The current `paper-simulations` folder has 30 configs:

- 5 schemes: `hpcc`, `dcqcn`, `timely`, `dctcp`, `hpcc_pint`
- 2 workloads: `ws`, `fb`
- 3 loads: `30`, `50`, `70`

That is broader than the original paper:

| Config family | How to interpret it |
|---|---|
| `hpcc_pint_*` | HPCC-PINT is from later work/project-page results, not the original 2019 HPCC paper. |
| `*_70.yml` | 70% load results are later HPCC project-page extensions, not the original paper's main evaluation. |
| `*_ws_70.yml`, `*_fb_70.yml` | Useful for stress testing, but compare them to the HPCC key-results page rather than Figure 10/11 in the 2019 paper. |
| `eta=99%` or `eta=150%` settings | Discussed on the later key-results page. The original paper text uses `eta=95%`. |

One subtle parameter note: the paper text reports `maxStage=5`, while the later HPCC results page says the paper's simulation setting was actually `maxStage=0` and that `maxStage=5` was a typo for simulation. Our configs use `mi_thresh: 0`, which matches that later clarification.

## Mapping To This Folder

The closest original-paper reproduction targets here are:

| Paper target | Local configs |
|---|---|
| Testbed-style WebSearch 30%/50% trend | `hpcc_ws_30.yml`, `dcqcn_ws_30.yml`, `hpcc_ws_50.yml`, `dcqcn_ws_50.yml` |
| Large-scale FB_Hadoop 50% trend | `hpcc_fb_50.yml`, `dcqcn_fb_50.yml`, `timely_fb_50.yml`, `dctcp_fb_50.yml` |
| Large-scale FB_Hadoop 30% plus incast | Requires the 30% background flow plus a separate 60-to-1 incast injection. |

Local reproduction caution: current `gen_traffic.sh` generates only the background workload traffic for `ws`/`fb` at each load. I do not see a separate 60-to-1 incast injection step for `*_fb_30`. That means `dcqcn_fb_30` without PFC pauses can be plausible for our current input, because it is not necessarily the same as the paper's Figure 11 30% plus incast case.

## What To Expect When Our Runs Are Correct

Before comparing performance, the run must pass integrity checks: valid traffic header, exact FCT row count, final drained status, valid PFC schema, valid qlen output, and valid bottleneck output.

After that, paper-consistent behavior should look like this:

| Signal | HPCC expectation | DCQCN/TIMELY expectation |
|---|---|---|
| Short-flow FCT tail | Much lower than alternatives, especially below 3 KB in WebSearch and below 120 KB in FB_Hadoop. | Higher tail slowdown due to standing queue and slower feedback. |
| Queue | Median near zero and tail far below MB-scale queueing under paper loads. | Standing queues can reach MB scale in the paper's WebSearch testbed results. |
| PFC | No PFC or near-zero PFC in original HPCC cases. | PFC appears mainly in the stressed 30% plus incast large-scale case; it may not appear in a background-only 30% run. |
| Long flows | Can be slightly worse for HPCC because of headroom and INT overhead. | May look better for long flows by filling buffers and using all residual capacity. |

So the core correctness story is not "HPCC always wins every metric." The original result is more specific: HPCC sharply improves latency and short-flow tail FCT by preventing standing queues and PFC, while accepting a controlled long-flow tradeoff from headroom and INT overhead.
