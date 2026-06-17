# HPCC Mini-Run Result Analysis

Date: 2026-05-16

This note interprets the artifacts currently under `examples/hpcc/algorithm-validation/output/`.
It is based on the existing output files only; no new simulations were run for this analysis.

## Reproduce The Summary

From the repo root:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --deep-trace
```

To save a full generated report:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --deep-trace --write examples/hpcc/algorithm-validation/output/analysis_report.md
```

## Overall Health

All current mini runs are internally consistent. Every run finishes with all flows completed and no remaining active flow state:

- `active=0`
- `qps=0`
- `pending=0`
- `bytes_left=0`
- `in_flight=0`
- `paused_q=0`

| Run | Flows | Final state | PFC events | Main bottleneck |
| --- | ---: | --- | ---: | --- |
| `hpcc_smoke` | `6/6` | drained | `42` | `sw0 port4 pg1` |
| `hpcc_incast` | `12/12` | drained | `990` | `sw0 port1 pg3` |
| `hpcc_pint_incast` | `12/12` | drained | `268` | `sw0 port1 pg3` |
| `dcqcn_incast` | `12/12` | drained | `30396` | `sw0 port1 pg3` |
| `dctcp_incast` | `12/12` | drained | `1008` | `sw0 port1 pg3` |
| `timely_incast` | `12/12` | drained | `358` | `sw0 port1 pg3` |
| `hpcc_mixed` | `10/10` | drained | `13388` | `sw1 port1 pg3` |

## Flow Completion Results

For the shared two-switch incast workload:

| Config | Mean FCT | Median FCT | Max FCT | Mean slowdown |
| --- | ---: | ---: | ---: | ---: |
| `hpcc_pint_incast` | `6.795 ms` | `5.451 ms` | `14.060 ms` | `74.2x` |
| `timely_incast` | `9.111 ms` | `9.136 ms` | `13.276 ms` | `113.1x` |
| `hpcc_incast` | `9.473 ms` | `6.250 ms` | `22.650 ms` | `97.5x` |
| `dctcp_incast` | `12.129 ms` | `12.028 ms` | `18.070 ms` | `149.3x` |
| `dcqcn_incast` | `85.561 ms` | `76.185 ms` | `151.801 ms` | `997.0x` |

Interpretation:

- `hpcc_pint_incast` has the best mean FCT in this mini workload and also the lowest PFC event count among the HPCC-like incast runs.
- `hpcc_incast` completes correctly, but its largest 400 KB flows have a longer tail than HPCC-PINT and TIMELY in this specific small setup.
- `dcqcn_incast` is the clear outlier: it completes, but slowly, with a very high PFC count. This is a useful signal for algorithm plumbing and parameter sensitivity, not a paper-level performance conclusion.
- `dctcp_incast` reports a large bottleneck ratio because its configured `kmax` is much smaller than HPCC/DCQCN/TIMELY for the same absolute queue size.

## Bottleneck And PFC Behavior

The two-switch topology intentionally creates a 25 Gbps inter-switch bottleneck while host links are 100 Gbps. For the incast workloads, the main bottleneck appears at `sw0 port1 pg3`, which matches the expected direction toward the cross-rack destination side.

The absolute max egress queue is similar across most incast configs:

- HPCC: about `1190 KB`
- HPCC-PINT: about `1184 KB`
- DCQCN: about `1185 KB`
- DCTCP: about `1178 KB`
- TIMELY: about `1184 KB`

PFC pause/resume records are balanced in every run. That matters because an unbalanced run would suggest the simulation left a paused queue asserted at the end.

The PFC records mostly appear on host nodes receiving pause/resume frames on `if=1`, which is consistent with backpressure propagating from the congested switch side toward senders.

## Queue Distribution

`qlen.txt` stores cumulative queue-length distributions. Each dump records, per switch port, how often the total egress queue length fell into each KB bucket since monitoring began.

The most important readout is the final cumulative distribution:

| Run | Max-port mean | P99 | Max |
| --- | ---: | ---: | ---: |
| `hpcc_smoke` | `6.86 KB` | `294 KB` | `1158 KB` |
| `hpcc_incast` | `59.72 KB` | `1112 KB` | `1190 KB` |
| `hpcc_pint_incast` | `22.67 KB` | `810 KB` | `1184 KB` |
| `dcqcn_incast` | `880.75 KB` | `1184 KB` | `1185 KB` |
| `dctcp_incast` | `37.05 KB` | `1128 KB` | `1177 KB` |
| `timely_incast` | `22.06 KB` | `966 KB` | `1183 KB` |
| `hpcc_mixed` | `165.03 KB` | `1126 KB` | `1166 KB` |

Interpretation:

- DCQCN keeps the bottleneck queue high for much longer in this mini run, which lines up with its high FCT and high PFC count.
- HPCC-PINT and TIMELY still hit high instantaneous queue peaks, but their mean queue occupancy is much lower.
- HPCC has a high tail queue in this incast case; the mean is moderate, but P99 is near the observed max.

## Trace Output

Only `hpcc_mixed` has tracing enabled. The other trace files contain a valid SimSetting header but no packet records.

For `hpcc_mixed`, the trace contains:

```text
records=3943528
data=3879424
ack_nack=23940
pfc=40164
host_records=991224
switch_records=2952304
```

This means the trace path is exercising both host-side and switch-side records and includes data, ACK/NACK, and PFC traffic. It is not just producing an empty file.

## Caveats

These results validate mechanics: scheduling, completion, bottleneck formation, PFC balance, queue sampling, and trace emission.

They should not be used as final performance claims against the HPCC paper. The topology and traffic are intentionally small, the workloads are synthetic, and the algorithm parameters are compact validation settings rather than calibrated paper-scale settings.

The right use of these results is to catch regressions and understand local behavior before moving to larger paper workloads.
