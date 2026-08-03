#!/usr/bin/env python3
"""Deployable-CC baselines on the parking lot (review response: is the
multi-bottleneck penalty HPCC-specific, or endemic to deployable RDMA CC?).

Runs DCQCN (cc_mode 1), TIMELY (7), DCTCP (8) — plus stock HPCC (3) and the
RCP mode (11) as anchors — on the N=2..4 parking lot with equal 50 MB flows,
simultaneous starts. Reports the unfairness ratio long-FCT / mean(cross-FCT)
(max-min oracle = 1.0) and PFC pause count.

Run from the repo root:
    venv/bin/python examples/hpcc/hpcc-fs/run_cc_baselines.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")

sys.path.insert(0, HERE)
import gen_parking_lot as gpl  # noqa: E402

SCHEMES = [(1, "DCQCN"), (7, "TIMELY"), (8, "DCTCP"), (3, "HPCC"), (11, "RDMA-RCP")]


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def run(n, cc):
    name = f"parking_lot_{n}bn_cc{cc}"
    # Harness parity with the original HPCC paper's evaluation: window-based
    # schemes (HPCC 3, RCP-INT 11) use the window; rate-only schemes
    # (DCQCN 1, TIMELY 7, DCTCP 8) run has_win=0 exactly as in the
    # validated algorithm-validation and repro configs.
    win = 0 if cc in (1, 7, 8) else 1
    gpl.build(n, flow_size=50_000_000, stop_time=0.2, bn_delay="0.002ms",
              has_win=win, var_win=("false" if win == 0 else "true"),
              suffix=f"_cc{cc}", cc_mode=cc)
    out = os.path.join(HERE, "output", name)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        return None
    long_src = n + 1
    lo, cr = None, []
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) < 7:
                continue
            (cr.append(int(p[6])) if ipid(p[0]) != long_src else None)
            if ipid(p[0]) == long_src:
                lo = int(p[6])
    if lo is None or len(cr) != n:
        return None
    pfcf = os.path.join(out, "pfc.txt")
    pfc = sum(1 for _ in open(pfcf)) if os.path.exists(pfcf) else 0
    return lo / (sum(cr) / len(cr)), pfc


def main():
    print(f"{'scheme':>9} | " + " | ".join(f"{'N='+str(n):>14}" for n in (2, 3, 4)))
    print("-" * 62)
    for cc, lab in SCHEMES:
        cells = []
        for n in (2, 3, 4):
            r = run(n, cc)
            cells.append(f"{r[0]:>7.3f}x p{r[1]:<4}" if r else f"{'FAIL':>12}")
        print(f"{lab:>9} | " + " | ".join(f"{c:>14}" for c in cells))


if __name__ == "__main__":
    main()
