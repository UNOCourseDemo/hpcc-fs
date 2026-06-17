# HPCC Algorithm Validation Mini Suite

This folder contains small, deterministic HPCC simulations for checking core RDMA congestion-control behavior before running the larger paper workloads.

## What It Covers

- `topologies/two_switch_6host.txt`: 2 switches and 6 hosts with a 25 Gbps inter-switch bottleneck and 100 Gbps host links.
- `flows/incast_bottleneck.txt`: synchronized cross-rack bursts that should create a visible bottleneck and ECN/PFC pressure.
- `flows/staggered_mixed.txt`: staggered bidirectional flows that exercise scheduling, routing, and mixed flow sizes.
- `configs/*_incast.yml`: same incast workload across HPCC, DCQCN, TIMELY, DCTCP, and HPCC-PINT.
- `configs/hpcc_mixed.yml`: HPCC on the mixed workload with packet tracing enabled.
- `configs/hpcc_smoke.yml`: smallest one-switch HPCC case. Start here; it should complete all flows.

## Run

From the repo root:

```bash
bash examples/hpcc/algorithm-validation/run.sh configs/hpcc_smoke.yml
```

Run all mini configs:

```bash
bash examples/hpcc/algorithm-validation/run_all.sh
```

Use a selected build profile. If the selected binary is missing, the runner
will build that profile through CMake before launching the simulation:

```bash
bash examples/hpcc/algorithm-validation/run.sh --optimized configs/hpcc_smoke.yml
```

Build and then run a selected profile:

```bash
bash examples/hpcc/algorithm-validation/run.sh --optimized --build configs/hpcc_smoke.yml
```

Build all supported profiles without running a simulation:

```bash
bash examples/hpcc/algorithm-validation/run.sh --build-all
```

The runner also accepts `--debug`, `--release`, `--build-only`,
`--no-auto-build`, and `--binary /path/to/executable`.

The runner changes into `examples/hpcc` before launching `hpcc-validation`, so paths inside the YAML files stay relative to the HPCC example directory.

Outputs are written to:

```text
examples/hpcc/algorithm-validation/output/<config-name>/
```

The runner treats an exit-0 simulation with missing or malformed artifacts as a validation failure. It checks FCT row count, FCT schema/ranges, exact flow identity coverage, per-queue PFC pause/resume balance, final pause state, bottleneck summary, and qlen monitor resolution.
When tracing is enabled, it also validates that the binary trace contains expected event classes and host/switch packet records.

Run a repeatability check for a single config:

```bash
bash examples/hpcc/algorithm-validation/check_determinism.sh configs/hpcc_smoke.yml
```

This runs the config twice and compares deterministic artifacts: `fct.txt`, `pfc.txt`, `bottleneck.txt`, `qlen.txt`, and `validation_checks.txt`.

Analyze existing output artifacts:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py --deep-trace
```

## Debug Notes

- `SMOKE_DEBUG.md`: root cause and fixes for the smoke-test `0/6` flow-completion failure, including the upstream comparison.
- `VALIDATION_CHECKS.md`: checks already performed, automated runner checks, determinism results, trace sanity results, and the remaining validation backlog.
- `RESULT_ANALYSIS.md`: interpretation of the current mini-run outputs.
- `ANALYSIS_TOOLS.md`: how to use `analyze_results.py` and what each metric means.
