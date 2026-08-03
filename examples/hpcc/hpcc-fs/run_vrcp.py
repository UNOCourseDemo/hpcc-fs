#!/usr/bin/env python3
"""Sender-side virtual RCP (mb_mode 6) vs switch RCP (cc_mode 11).

The decisive negative-result experiment (review response). RCP's inputs
(C, y, q) are all sender-visible in HPCC's INT, so a sender can mirror the
switch's per-port recursion per hop and adopt the path-min (mb_mode 6,
rate-only, same gains/init/clamps). If the obstacle were INFORMATION, this
variant would equal switch RCP everywhere. The prediction is that it fails
under arrival asynchrony: the multiplicative recursion driven by a common
observed y preserves the RATIO between senders' virtual estimates, so a
late-arriving flow's fresh R0 never converges to the incumbents' evolved R
-- the obstacle is CONSISTENCY of one shared reference, which per-port
switch state provides and private sender state cannot.

Scenarios on the N=4 parking lot (50 MB flows):
  sim       all flows start at t=0 (synchronized, identical init)
  stagL     cross flows at t=0, long flow at t=+5 ms (late arrival)
  stagC     long flow at t=0, cross flows at t=+5 ms

Run from the repo root:
    venv/bin/python examples/hpcc/hpcc-fs/run_vrcp.py
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

N = 4


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def run(tag, cc, mb, long_start=0.0, cross_start=0.0):
    name = f"parking_lot_{N}bn_{tag}"
    # mb6 runs rate-only (has_win=0) for parity with cc11's window-off default.
    win = 0 if mb == 6 else 1
    gpl.build(N, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
              has_win=win, var_win=("false" if win == 0 else "true"),
              suffix=f"_{tag}", cc_mode=cc, mb_mode=mb,
              long_start=long_start, cross_start=cross_start)
    out = os.path.join(HERE, "output", name)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        return None
    long_src = N + 1
    lo, cr = None, []
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) < 7:
                continue
            if ipid(p[0]) == long_src:
                lo = int(p[6])
            else:
                cr.append(int(p[6]))
    if lo is None or len(cr) != N:
        return None
    pfcf = os.path.join(out, "pfc.txt")
    pfc = sum(1 for _ in open(pfcf)) if os.path.exists(pfcf) else 0
    return lo / (sum(cr) / len(cr)), pfc


def main():
    scen = [("sim", 0.0, 0.0), ("stagL", 0.005, 0.0), ("stagC", 0.0, 0.005)]
    print(f"{'variant':>22} | " + " | ".join(f"{s[0]:>12}" for s in scen))
    print("-" * 70)
    for lab, cc, mb in (("switch RCP (cc11)", 11, 0),
                        ("sender vRCP (mb6)", 3, 6)):
        cells = []
        for stag, ls, cs in scen:
            r = run(f"{'m6' if mb else 'c11'}_{stag}", cc, mb, ls, cs)
            cells.append(f"{r[0]:>7.3f}x p{r[1]:<3}" if r else f"{'FAIL':>11}")
        print(f"{lab:>22} | " + " | ".join(f"{c:>12}" for c in cells))


if __name__ == "__main__":
    main()
