# HPCC Paper Simulation Integrity Notes

Date: 2026-05-17

## What Was Wrong

`output/hpcc_fb_30` completed, but it was produced from a malformed traffic file:

- `traffic/flow_fb_30.txt` header said `996506` flows.
- The file contained only `948931` data rows.
- The simulator scheduled `996506` flows anyway because the flow parser did not check extraction failure after the short file ended.
- The final parsed flow was therefore reused many times, creating an artificial tail around `155 ms`.

That old `hpcc_fb_30` output should not be used as a paper result. After repairing the traffic file, the analyzer now reports:

```text
fct.txt has 996506 row(s), expected 995249 from flow_file
missing bottleneck.txt
```

This is expected until `hpcc_fb_30` is rerun with the repaired traffic and regenerated config.

## Fixes Applied

- `traffic_gen_uno/traffic_gen.py` now writes traffic atomically through a temporary file and only replaces the final output after generation completes.
- The traffic generator writes a fixed-width header and rewrites it with the actual generated flow count, avoiding stale digits.
- `paper-simulations/run.sh` now validates traffic files before running a simulation.
- If an existing traffic file is invalid, the runner moves it to `*.invalid.<timestamp>` and regenerates it.
- `hpcc-validation.cc` now validates the flow file before building/running the simulation and aborts on malformed flow rows.
- Paper YAML configs were regenerated so they include `pause_time`, queue monitor intervals, and `bottleneck_output_file`.
- The paper runner now writes `validation_checks.txt` after successful runs and verifies FCT count, PFC schema, qlen output, bottleneck output, and final drained status.
- The analysis tool now checks the run's configured `flow_file` against `fct.txt` and buckets paper-scale FCT-by-size reports.

## Current Input State

The bad `flow_fb_30.txt` was moved aside as:

```text
traffic/flow_fb_30.txt.invalid.20260517-161545
```

The repaired `traffic/flow_fb_30.txt` validates with:

```text
995249 flows
```

Existing local traffic inputs checked and passed:

```text
flow_fb_30.txt: 995249 flows
flow_ws_30.txt: 69635 flows
flow_ws_50.txt: 117068 flows
```

## Commands Used

Validate selected paper inputs without building or running:

```bash
bash examples/hpcc/paper-simulations/run.sh --check-inputs configs/hpcc_fb_30.yml configs/hpcc_ws_30.yml configs/hpcc_ws_50.yml
```

Generate or repair traffic only:

```bash
bash examples/hpcc/paper-simulations/run.sh --traffic-only configs/hpcc_fb_30.yml
```

Analyze existing paper outputs:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py \
  --output-root examples/hpcc/paper-simulations/output \
  --configs hpcc_fb_30 \
  --no-explain
```

## Original-Code Comparison

The local original-style `hpcc-haoyu.cc` has the same unchecked flow read pattern:

```text
flowf >> flow_input.src >> flow_input.dst >> ...
```

without verifying that the extraction succeeded. The local original traffic generator also writes directly to the final output path and rewrites the header at the end, so an interrupted generation can leave a truncated file with the old estimated header. The refactor now guards both failure modes.

## Required Next Step

Rerun `hpcc_fb_30` before using it for algorithm or paper comparison:

```bash
bash examples/hpcc/paper-simulations/run.sh --optimized configs/hpcc_fb_30.yml
```

That run should produce a new `bottleneck.txt` and `validation_checks.txt`. A valid result should have zero analyzer warnings, `Input OK=yes`, `Flows=Input Flows`, and `Drained=yes`.
