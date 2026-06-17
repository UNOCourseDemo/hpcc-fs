# HPCC Result Analysis Tools

This folder includes a self-service parser for the mini validation outputs:

```text
examples/hpcc/algorithm-validation/analyze_results.py
```

Use the project venv from the repo root:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py
```

The tool reads existing output artifacts. It does not build ns-3 and does not run simulations.

## Common Commands

Generate a human-readable Markdown report:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py
```

Include deep binary trace counters for trace-enabled runs:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --deep-trace
```

Save a report:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --deep-trace --write examples/hpcc/algorithm-validation/output/analysis_report.md
```

Compare only selected runs:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --configs hpcc_incast hpcc_pint_incast timely_incast
```

Emit CSV for a spreadsheet:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --format csv
```

Emit full JSON for custom analysis:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --format json
```

Analyze a different output root:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --output-root path/to/output
```

## What The Tool Reads

For each output directory, the tool looks for:

| File | Meaning |
| --- | --- |
| `simulation.log` | Final simulator status, elapsed wall time, event count, and drained-flow state. |
| `config.yml` | Run config copy. Used to locate the original `flow_file` for input/FCT count checks. |
| `fct.txt` | One row per completed flow. Used for FCT, standalone FCT, slowdown, and size grouping. |
| `pfc.txt` | PFC pause/resume events. Used for event counts, balance, first/last event time, and affected queues. |
| `bottleneck.txt` | Sampled queue-pressure summary by switch, port, and priority group. |
| `qlen.txt` | Cumulative queue-length distribution by switch port. |
| `trace.tr` | Binary packet trace. Header is always present; packet records exist when tracing is enabled. |
| `validation_checks.txt` | Runner validation result summary. |

## Metric Meanings

`Drained`

The final status reports that all flows started and completed, and that no sender or queue state remains active:

```text
active=0 qps=0 pending=0 bytes_left=0 in_flight=0 paused_q=0
```

`FCT`

Flow completion time. In `fct.txt`, this is column 7, measured in nanoseconds. The tool reports it in milliseconds.

`Input OK`

The configured `flow_file` exists, has a single integer header, has exactly that many valid data rows, and is sorted by start time. For paper-scale runs, this catches truncated traffic files before FCT tail numbers are trusted.

`Standalone FCT`

The simulator's no-contention baseline estimate for that flow. It is column 8 in `fct.txt`.

`Slowdown`

```text
slowdown = fct_ns / standalone_fct_ns
```

This helps compare flows of different sizes. A high slowdown means the flow took much longer than its no-contention baseline.

`PFC events`

Rows in `pfc.txt`. Type `1` is pause and type `0` is resume. A healthy completed run should generally have balanced pause/resume counts and final `paused_q=0`.

`PFC queues`

Unique `(node_id, node_type, if_index, qIndex)` tuples that saw PFC events. This helps identify which senders or ports were backpressured.

`Bottleneck`

The reported bottleneck row is the nonzero priority group with the largest sampled:

```text
max_egress_bytes / kmax
```

This identifies where queue pressure was strongest relative to that port's ECN threshold.

`Q/Kmax`

The maximum sampled queue divided by configured `kmax`. Values above `1.0` mean the queue exceeded the ECN max threshold at least once.

`ECN`

In `bottleneck.txt`, `ecn_seen=1` means sampled egress queue crossed `kmin` at least once for that row.

`Pause`

In `bottleneck.txt`, `pause_seen=1` means the sampled row saw MMU pause pressure, headroom use, or shared-buffer pressure crossing the PFC threshold.

`Qlen`

`qlen.txt` is cumulative. At each `time:` block, every switch-port row is a histogram of total egress queue length in KB buckets from monitoring start through that dump.

The tool reports the final cumulative distribution:

- mean queue occupancy in KB
- P95 and P99 KB bucket
- max observed KB bucket

`Trace records`

The binary trace begins with a SimSetting header. Packet records follow only when `enable_trace: 1`. Without `--deep-trace`, the tool counts record totals from file size. With `--deep-trace`, it also counts data, ACK/NACK, PFC, host-side records, and switch-side records.

## How To Read The Current Results

For the current mini suite, the most useful sanity questions are:

- Did every run drain? If no, inspect `simulation.log` and `validation_checks.txt` first.
- Did every scheduled flow emit one FCT row? If no, inspect `fct.txt` and the flow file identity check.
- Does `Input OK` say yes and does `Flows` match `Input Flows`? If no, fix/rerun the traffic before interpreting FCT.
- Are PFC pause/resume counts balanced? If no, inspect `pfc.txt` per queue.
- Is the main incast bottleneck on the expected inter-switch port? For the two-switch incast configs, this should be `sw0 port1 pg3`.
- Is a run's high FCT also visible in queue or PFC behavior? In the current outputs, DCQCN has high FCT, high PFC count, and high mean bottleneck queue occupancy.
- Is tracing truly active? In the current outputs, only `hpcc_mixed` has packet trace records; the other configs have trace headers only.

## Practical Caveats

The analysis tool summarizes validation behavior. It does not decide whether an algorithm is paper-correct.

Small validation workloads are intentionally synthetic, and the metrics are sensitive to topology, flow timing, ECN thresholds, PFC settings, and rate-control parameters. Use these reports to catch regressions and inspect behavior before running larger paper-scale experiments.

For paper-scale outputs with many unique flow sizes, Markdown reports automatically group FCT by size bucket (`<1KB`, `1-10KB`, `10-100KB`, `100KB-1MB`, `1-10MB`, `>=10MB`) so the report remains readable.
