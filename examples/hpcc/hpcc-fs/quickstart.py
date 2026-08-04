#!/usr/bin/env python3
"""One-command artifact quickstart: generate the N=4 parking lot, run RDMA-RCP
(cc_mode 11), and print the headline fairness result.

Run from the repository root, after building the optimized binary:
    bash examples/hpcc/algorithm-validation/run.sh --optimized --build-only
    python3 examples/hpcc/hpcc-fs/quickstart.py
Expected: UNFAIRNESS ~= 1.005x, PFC = 0 (deterministic).
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


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def main():
    if not os.path.exists(BIN):
        sys.exit("optimized binary not found -- build first:\n"
                 "  bash examples/hpcc/algorithm-validation/run.sh --optimized --build-only")
    gpl.build(4, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="", cc_mode=11)
    rc = subprocess.run([BIN, "hpcc-fs/configs/hpcc_parking_lot_4bn.yml"],
                        cwd=HPCC_DIR).returncode
    assert rc == 0, f"simulation exited {rc}"
    per = {}
    with open(os.path.join(HERE, "output", "parking_lot_4bn", "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) >= 7:
                per.setdefault(ipid(p[0]), []).append(int(p[6]))
    lo = per[5][0]
    cr = [v[0] for k, v in per.items() if k != 5]
    pfcf = os.path.join(HERE, "output", "parking_lot_4bn", "pfc.txt")
    pfc = sum(1 for ln in open(pfcf) if ln.split()[5] == "1") if os.path.exists(pfcf) else 0
    print(f"\nUNFAIRNESS (long / mean-cross FCT) = {lo/(sum(cr)/len(cr)):.3f}x   PFC = {pfc}")
    print("expected: 1.005x, PFC = 0")


if __name__ == "__main__":
    main()
