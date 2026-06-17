# HPCC Algorithm Validation Checks

This file records the checks already performed on the mini validation suite and the next checks worth adding after completion, PFC, bottleneck, queue-monitor, trace, and determinism validation.

## Checks Performed And Passed

Date: 2026-05-16

Build command:

```bash
/opt/homebrew/bin/cmake --build /Users/tiffanyzhang/uno-hpcc/cmake-build-debug --target hpcc-validation -j 14
```

Result: passed. The build still emits existing compiler warnings, but the `hpcc-validation` target links successfully.

Validation commands:

```bash
bash examples/hpcc/algorithm-validation/run.sh configs/hpcc_smoke.yml
bash examples/hpcc/algorithm-validation/run.sh configs/hpcc_incast.yml
```

Passed checks:

| Check | `hpcc_smoke` | `hpcc_incast` | Why it matters |
| --- | --- | --- | --- |
| Process exit | `exit=0` | `exit=0` | The simulator did not crash or assert. |
| Expected FCT row count | `6/6` | `12/12` | Every scheduled flow emitted a completion record. |
| Final flow status | `started=6/6 completed=6 pending=0 active=0 qps=0` | `started=12/12 completed=12 pending=0 active=0 qps=0` | No flow or QP was stuck at `simulator_stop_time`. |
| Final byte status | `bytes_left=0 in_flight=0` | `bytes_left=0 in_flight=0` | Sender state drained cleanly after completion. |
| FCT positivity | `0` non-positive FCT rows | `0` non-positive FCT rows | Completion times are sane and not zero/negative. |
| Max FCT before stop time | `3,790,692 ns < 0.2 s` | `22,649,766 ns < 0.2 s` | The configured stop time has enough margin for these workloads. |
| PFC path exercised | `42` PFC events | `990` PFC events | The PFC code path runs without the refactor RNG crash. |
| PFC pause/resume balance | `21` pause, `21` resume | `495` pause, `495` resume | No obvious global PFC pause leak in these runs. |
| Output artifacts | `simulation.log`, `fct.txt`, `pfc.txt`, `bottleneck.txt`, `qlen.txt`, copied `config.yml` | same | The runner leaves enough artifacts for post-run inspection. |
| FCT schema/range automation | passed | passed | Runner now fails malformed FCT rows, non-positive sizes/times, or completions after `simulator_stop_time`. |
| Flow identity coverage automation | passed | passed | Runner now matches completed flows against the exact requested flow identities, not only the row count. |
| PFC semantic automation | passed | passed | Runner now validates PFC schema, per-queue pause/resume balance, and final `paused_q=0`. |
| Bottleneck summary automation | passed | passed | Runner now validates sampled max queue/bottleneck pressure from `bottleneck.txt`. |
| Queue monitor resolution automation | passed | passed | Runner now requires multiple `qlen.txt` dumps and nonzero samples. |
| Trace sanity automation | skipped, trace disabled | skipped, trace disabled | Runner skips cleanly when `enable_trace: 0` and validates binary trace structure when enabled. |

Notes:

- `fct.txt` format is `sip dip sport dport size_bytes start_time_ns fct_ns standalone_fct_ns`.
- `pfc.txt` format is currently `time_ns node_id node_type if_index qIndex type`, where type `1` is pause and type `0` is resume.
- `bottleneck.txt` format is `sw port pg max_egress_bytes kmin kmax max_ratio max_shared_bytes max_ingress_bytes max_hdrm_bytes min_pfc_threshold ecn_seen pause_seen samples`, plus a `max_overall` row.
- `qlen.txt` is now sampled at the configured mini-run resolution (`qlen_mon_interval: 10000`, `qlen_dump_interval: 1000000`) across the full `0.2 s` mini run.
- `trace.tr` is validated for configs with `enable_trace: 1`; configs with tracing disabled record an explicit skip line in `validation_checks.txt`.
- Each run now writes `validation_checks.txt` beside its normal outputs.

## Full Mini Matrix Check

Date: 2026-05-16

Command:

```bash
bash examples/hpcc/algorithm-validation/run_all.sh
```

Result: `7/7` mini configs passed expected-flow count, FCT schema/range checks, FCT identity coverage, PFC semantic checks, bottleneck summary checks, qlen resolution checks, and trace sanity handling.

| Config | Result |
| --- | --- |
| `dcqcn_incast` | `12/12` flows, `30396` PFC events, validation checks passed |
| `dctcp_incast` | `12/12` flows, `1008` PFC events, validation checks passed |
| `hpcc_incast` | `12/12` flows, `990` PFC events, validation checks passed |
| `hpcc_mixed` | `10/10` flows, `13388` PFC events, validation checks passed |
| `hpcc_pint_incast` | `12/12` flows, `268` PFC events, validation checks passed |
| `hpcc_smoke` | `6/6` flows, `42` PFC events, validation checks passed |
| `timely_incast` | `12/12` flows, `358` PFC events, validation checks passed |

## Trace Sanity Check

Date: 2026-05-16

Command:

```bash
bash examples/hpcc/algorithm-validation/run.sh configs/hpcc_mixed.yml
```

Result: passed.

The mixed workload has `enable_trace: 1`, so the runner parsed `trace.tr` as a binary SimSetting header followed by fixed-size trace records. The check passed with:

```text
records=3943528 recv=1476152 enqu=991224 dequ=1476152 drop=0 data=3879424 ack_nack=23940 pfc=40164 cnp=0 host_records=991224 switch_records=2952304
```

The runner now validates:

- Trace file exists and is non-empty when `enable_trace: 1`.
- SimSetting header has a valid port count.
- Remaining payload size is a multiple of the expected `TraceFormat` record size.
- Trace records contain receive, enqueue, and dequeue event classes.
- Trace records include RDMA data packets and ACK/NACK packets.
- Trace records include both host-side and switch-side records.

This check catches broken tracing output, missing packet classes, and trace format drift after refactors.

## Determinism Check

Date: 2026-05-16

Commands:

```bash
bash examples/hpcc/algorithm-validation/check_determinism.sh configs/hpcc_smoke.yml
bash examples/hpcc/algorithm-validation/check_determinism.sh configs/hpcc_incast.yml
```

Result: both passed.

The determinism script runs the same config twice and compares these artifacts byte-for-byte:

- `fct.txt`
- `pfc.txt`
- `bottleneck.txt`
- `qlen.txt`
- `validation_checks.txt`

Reports:

- `output/hpcc_smoke_determinism_20260515234249/determinism_report.txt`: all hashes matched.
- `output/hpcc_incast_determinism_20260515234256/determinism_report.txt`: all hashes matched.

`simulation.log` is intentionally excluded because it contains wall-clock elapsed times and progress timing that can vary without changing simulation behavior.

## Automated FCT Checks Added

The runner now validates:

- FCT file exists and is non-empty.
- Every FCT row has 8 columns.
- IP fields are hex and numeric fields are unsigned integers.
- `size_bytes`, `fct_ns`, and `standalone_fct_ns` are positive.
- `start_time_ns + fct_ns <= simulator_stop_time`.
- Parsed flow-file row count matches its header.
- Every expected flow maps to one completed FCT row using source IP, destination IP, generated source port, destination port, size, and start time.
- No unexpected or duplicate FCT flow identity appears.

The flow identity check cannot validate priority group directly because `fct.txt` does not currently include PG. Source/destination, ports, size, and start time still catch the practical wrong-flow and duplicate-flow cases in these configs.

## Automated PFC, Bottleneck, And Qlen Checks Added

The runner now validates:

- `pfc.txt` exists and every row has 6 columns.
- PFC event fields are unsigned integers, and type is `0` resume or `1` pause.
- Pause/resume balance is checked per `(node_id, node_type, if_index, qIndex)`.
- A resume before a matching pause fails the run.
- The final status line must have `paused_q=0`.
- `bottleneck.txt` exists and contains a `max_overall` sampled pressure row.
- The bottleneck summary must have samples and must observe queued bytes.
- If PFC events occurred, the bottleneck summary must have seen ECN or pause pressure.
- `qlen.txt` exists, has at least two `time:` dumps, has switch-port rows, and has nonzero samples.

The mini configs now set:

```yaml
qlen_dump_interval: 1000000
qlen_mon_interval: 10000
qlen_mon_start: 0
qlen_mon_end: 200000000
```

That gives 200 queue-distribution dumps over the 0.2 s mini runs.

## What To Check Next

1. No-congestion baseline

   Add a tiny non-incast config where no bottleneck should form. Expected result: all flows complete, PFC count is zero or near zero, and FCT is close to standalone FCT.

2. Stop-time guardrail

   Keep the runner's existing row-count check, but also fail if the final status has `active > 0`, `qps > 0`, `bytes_left > 0`, or `in_flight > 0`.
