# Paper Simulation Configs

This folder contains ready-to-run YAML configs and scripts to reproduce the
simulations from the HPCC SIGCOMM 2019 paper.

## Structure

```
paper-simulations/
├── README.md                 ← This file
├── gen_configs.py            ← Generates all 30 YAML configs
├── gen_traffic.sh            ← Generates all traffic files
├── run_all.sh                ← Run one, many, or all simulations
├── ORIGINAL_PAPER_RESULTS_SUMMARY.md ← Published HPCC paper result targets
├── RESULT_ANALYSIS.md        ← Local integrity findings and repair notes
├── configs/                  ← 30 YAML configs (scheme × workload × load)
│   ├── hpcc_ws_30.yml
│   ├── hpcc_ws_50.yml
│   ├── dcqcn_fb_70.yml
│   └── ...
├── traffic/                  ← Generated traffic files
│   ├── flow_ws_30.txt
│   ├── flow_ws_50.txt
│   └── ...
└── output/                   ← Results (one subdirectory per run)
    ├── hpcc_ws_50/
    │   ├── config.yml        ← Copy of config used
    │   ├── simulation.log    ← Full stdout/stderr
    │   ├── fct.txt           ← Flow completion times
    │   ├── pfc.txt           ← PFC events
    │   ├── trace.tr          ← Packet trace (if enabled)
    │   └── qlen.txt          ← Queue length distribution
    ├── dcqcn_ws_50/
    │   └── ...
    └── ...
```

## Usage

```bash
# 1. Generate traffic files (once)
bash gen_traffic.sh

# 2a. Run a SINGLE simulation
bash run_all.sh configs/hpcc_ws_50.yml

# 2b. Run a SUBSET (glob pattern)
bash run_all.sh configs/hpcc_*.yml
bash run_all.sh configs/*_ws_50.yml
bash run_all.sh configs/dcqcn_fb_30.yml configs/timely_fb_30.yml

# 2c. Run ALL simulations
bash run_all.sh

# 2d. Run with an optimized hpcc-validation binary.
#     If it is missing, the runner builds it through CMake first.
bash run_all.sh --optimized configs/hpcc_ws_50.yml

# 2e. Build the optimized binary, then run
bash run_all.sh --optimized --build configs/hpcc_ws_50.yml

# 2f. Build debug, release, and optimized binaries without running
bash run_all.sh --build-all

# 2g. Validate paper inputs without generating traffic or running
bash run_all.sh --check-inputs configs/hpcc_fb_30.yml configs/hpcc_ws_30.yml

# 2h. Generate/repair traffic only
bash run_all.sh --traffic-only configs/hpcc_fb_30.yml
```

The runner also accepts `--debug`, `--release`, `--build-only`,
`--force-traffic`, `--no-auto-build`, and `--binary /path/to/executable`.

Before each simulation, the runner validates the configured traffic file:
header count, row count, schema, host IDs, positive flow sizes, priority group,
and nondecreasing start time. After each successful simulation, it writes
`validation_checks.txt` and verifies FCT row count, PFC schema, qlen output,
bottleneck output, and final drained status.

## Analyze Results

For a source-grounded summary of the published SIGCOMM 2019 result targets,
read `ORIGINAL_PAPER_RESULTS_SUMMARY.md` first. It also notes which local
configs are later HPCC/PINT extensions rather than original-paper figures.

Use the shared analysis tool from the project venv:

```bash
venv/bin/python examples/hpcc/algorithm-validation/analyze_results.py \
  --output-root examples/hpcc/paper-simulations/output \
  --configs hpcc_fb_30 \
  --no-explain
```

For paper-scale runs, the Markdown report groups FCT by size bucket instead of
printing one row per exact flow size.

## Config Naming Convention

`<cc_scheme>_<workload>_<load>.yml`

| Token | Values |
|-------|--------|
| cc_scheme | `hpcc`, `dcqcn`, `timely`, `dctcp`, `hpcc_pint` |
| workload | `ws` (Web Search), `fb` (Facebook Hadoop) |
| load | `30`, `50`, `70` (percent) |
