# Paper Simulation Result Summary

Date: 2026-05-17

This summarizes the paper-simulation outputs currently present under `output/`.
It is a result-integrity summary, not a final paper comparison yet.

Generated companion files:

- `paper_results_summary.csv`: flat machine-readable metrics.
- `paper_results_detailed.md`: analyzer tables with FCT size buckets, PFC, queue, trace, and warnings.

## Overall Status

No current paper output should be treated as a fully validated final result yet.

`dcqcn_fb_30` is the closest: its input count matches its FCT count and the final
status line reports all flows drained, but the run log does not include
`Simulation Complete`, no `validation_checks.txt` exists, `bottleneck.txt` is
empty, and queue monitoring stopped before the configured end. Treat it as
FCT-complete but run-finalization incomplete.

`hpcc_fb_30` is explicitly invalid. It was generated before the flow-file repair:
the old traffic header was larger than the actual number of flow rows, so the
simulator reused a stale final flow and created an artificial FCT tail.

The web-search HPCC outputs are partial/interrupted and cannot be used for
algorithm comparison.

## Run Table

| Run | Status | Input Flows | FCT Rows | Drained | Mean FCT ms | P90 FCT ms | Max FCT ms | Mean Slowdown | PFC Events | Queue Max |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `dcqcn_fb_30` | FCT-complete, finalization incomplete | 995249 | 995249 | yes | 0.041 | 0.057 | 8.913 | 1.6x | 0 | 3057 KB |
| `hpcc_fb_30` | invalid, stale traffic artifact | 995249 | 996506 | yes, but from bad input | 7.405 | 0.067 | 155.539 | 480.1x | 0 | 547 KB |
| `hpcc_ws_30` | incomplete/interrupted | 69635 | 29099 | no | 0.313 | 0.907 | 14.030 | 1.6x | 0 | 0 KB |
| `hpcc_ws_50-1` | incomplete/inconsistent artifacts | 117068 | 107480 | no | 66.286 | 238.890 | 659.445 | 984.8x | 18370177 | 24344 KB |

## Notes By Run

### `dcqcn_fb_30`

- Flow accounting is good: `995249/995249` FCT rows.
- The latest status line reports `started=995249/995249`, `completed=995249`,
  `pending=0`, `active=0`, `bytes_left=0`, and `in_flight=0`.
- FCT is low: median `0.01289 ms`, p90 `0.05652 ms`, max `8.912704 ms`.
- No PFC events were recorded.
- Queue distribution reached only `2.5 s`; configured monitoring should reach
  `3.0 s`.
- `bottleneck.txt` is empty because the run did not reach normal finalization.

### `hpcc_fb_30`

- Do not use for paper comparison.
- Current repaired input has `995249` flows, but this output has `996506` FCT
  rows from the old malformed traffic file.
- The large `10-100KB` tail (`p90 ~= 154 ms`, max `155.539 ms`) is an input
  artifact, not reliable HPCC behavior.
- This run is marked in `output/hpcc_fb_30/INVALID_RESULT.md`.

### `hpcc_ws_30`

- Incomplete: only `29099/69635` FCT rows exist.
- Latest status line was around `2.041803/4.0 s`, with `active=250`,
  `pending=40331`, `bytes_left=1371202676`, and `in_flight=14783813`.
- No `Simulation Complete` marker and no bottleneck summary.
- FCT statistics describe only completed early flows.

### `hpcc_ws_50-1`

- Incomplete/inconsistent: `107480/117068` FCT rows exist, but the final visible
  log status is much earlier and still has many pending flows.
- PFC was extremely heavy: `18370177` events, with unbalanced pause/resume counts.
- `pfc.txt` has a malformed trailing row, and `bottleneck.txt` is missing.
- Queue pressure was high: max qlen bucket `24344 KB`, p99 `19493 KB` on
  `sw354/p1`.

## Recommended Next Steps

1. Rerun `hpcc_fb_30` with repaired traffic:

   ```bash
   bash examples/hpcc/paper-simulations/run.sh --optimized configs/hpcc_fb_30.yml
   ```

2. Rerun `dcqcn_fb_30` if you need complete queue/bottleneck artifacts:

   ```bash
   bash examples/hpcc/paper-simulations/run.sh --optimized configs/dcqcn_fb_30.yml
   ```

3. Rerun the web-search HPCC cases from clean output directories before using
   them for comparison.

4. After each rerun, require:

   - `validation_checks.txt` exists and contains only `OK:` lines.
   - Analyzer reports `Input OK=yes`.
   - `Flows` equals `Input Flows`.
   - `Drained=yes`.
   - `bottleneck.txt` has a `max_overall` row.
   - No analyzer warnings.
