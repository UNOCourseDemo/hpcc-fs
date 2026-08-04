#!/usr/bin/env python3
"""ECMP hash-seed sensitivity on the k=4 fat-tree (review response).

Runs the gen_fattree_k4 workload under stock HPCC (cc_mode 3) and HPCC-FS
(cc_mode 11) across several ECMP hash-seed offsets (the additive
`ecmp_seed_offset` knob shifts every switch's hash seed; 0 = stock seeds)
and reports the raw long/short mean-FCT ratio per seed. Long flows are the
4 inter-pod (5-switch) flows, short the 4 intra-pod different-edge flows.

Run from the repo root:
    venv/bin/python examples/hpcc/hpcc-fs/run_ecmp_seeds.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # examples/hpcc/hpcc-fs
HPCC_DIR = os.path.dirname(HERE)                            # examples/hpcc
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))           # repo root
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")

sys.path.insert(0, HERE)
import gen_fattree_k4 as g4  # noqa: E402

SEEDS = [0] + [101 * i for i in range(1, 20)]
LONG_SRC = {20, 22, 24, 26}
SHORT_SRC = {21, 25, 29, 33}


def ip_to_id(hexip: str) -> int:
    return (int(hexip, 16) >> 8) & 0xFFFF


def run(name: str, seed: int) -> float:
    cfg = os.path.join(HERE, "configs", f"hpcc_{name}.yml")
    if seed != 0:
        with open(cfg, "a") as f:
            f.write(f"ecmp_seed_offset: {seed}\n")
    out = os.path.join(HERE, "output", name)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(f"{name} failed (exit {rc})")
    longs, shorts = [], []
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) < 7:
                continue
            src, fct = ip_to_id(p[0]), int(p[6])
            (longs if src in LONG_SRC else shorts if src in SHORT_SRC else []).append(fct)
    assert len(longs) == 4 and len(shorts) == 4, f"{name}: {len(longs)}L/{len(shorts)}S"
    return (sum(longs) / 4) / (sum(shorts) / 4)


def main():
    print(f"{'seed':>6} | {'stock HPCC':>11} | {'HPCC-FS':>8}")
    ratios = {3: [], 11: []}
    for s in SEEDS:
        row = {}
        for cc in (3, 11):
            name = f"ft4_ecmp_cc{cc}_s{s}"
            g4.build(name, cc_mode=cc)
            row[cc] = run(name, s)
            ratios[cc].append(row[cc])
        print(f"{s:>6} | {row[3]:>10.3f}x | {row[11]:>7.3f}x")
    for cc, lab in ((3, "stock"), (11, "HPCC-FS")):
        v = ratios[cc]
        print(f"{lab}: raw long/short ratio range [{min(v):.3f}, {max(v):.3f}], "
              f"mean {sum(v)/len(v):.3f}")


if __name__ == "__main__":
    main()
