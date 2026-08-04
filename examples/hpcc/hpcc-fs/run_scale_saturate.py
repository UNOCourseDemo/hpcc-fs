#!/usr/bin/env python3
"""Saturating k=6 fat-tree workload (round-3 MC9).

Every one of the 54 hosts sends two 20 MB flows to hosts in two different
pods (offsets +9 and +27 in host index), all starting at t=0: 108 inter-pod
flows. Per-pod uplink demand equals uplink capacity at the max-min share
(12.5 Gbps/flow), so cores and agg-edge stages are simultaneously saturated
and ECMP collisions create persistent contention.

Identical, symmetric, all-cross-pod flows => the fair allocation implies
near-equal FCTs. We report makespan (max FCT), mean FCT, Jain's index over
the 108 FCTs, and PFC pauses, stock HPCC vs RDMA-RCP.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_scale_saturate.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")
sys.path.insert(0, HERE)
import gen_fattree as gf  # noqa: E402

K = 6
N_HOST = K * (K // 2) * (K // 2)          # 54
HOST0 = (K // 2) ** 2 + 2 * K * (K // 2)  # 45 switches before hosts
SIZE = 20_000_000


def main():
    print(f"== saturating k={K} fat-tree: {2*N_HOST} inter-pod flows x {SIZE//1_000_000} MB ==")
    print(f"  {'scheme':>10} {'makespan ms':>12} {'mean FCT ms':>12} {'Jain':>6} {'PFC':>6}")
    for cc, lab in ((3, "HPCC"), (11, "RDMA-RCP")):
        name = f"ft6_sat_cc{cc}"
        gf.build(name, k=K, cc_mode=cc, flow_size=SIZE, stop=0.3)
        flows = [str(2 * N_HOST)]
        for i in range(N_HOST):
            for off in (9, 27):
                flows.append(f"{HOST0+i} {HOST0+(i+off)%N_HOST} 3 100 {SIZE} 0.000000")
        with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as fh:
            fh.write("\n".join(flows) + "\n")
        out = os.path.join(HERE, "output", name)
        os.makedirs(out, exist_ok=True)
        for fn in os.listdir(out):
            os.remove(os.path.join(out, fn))
        with open(os.path.join(out, "sim.log"), "w") as log:
            rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                                stdout=log, stderr=subprocess.STDOUT).returncode
        assert rc == 0, name
        fcts = []
        with open(os.path.join(out, "fct.txt")) as fh:
            for ln in fh:
                p = ln.split()
                if len(p) >= 7 and int(p[4]) == SIZE:
                    fcts.append(int(p[6]))
        assert len(fcts) == 2 * N_HOST, f"{name}: {len(fcts)} flows finished"
        jain = sum(fcts) ** 2 / (len(fcts) * sum(f * f for f in fcts))
        pfcf = os.path.join(out, "pfc.txt")
        pfc = sum(1 for _ in open(pfcf)) if os.path.exists(pfcf) else 0
        print(f"  {lab:>10} {max(fcts)/1e6:>12.2f} {sum(fcts)/len(fcts)/1e6:>12.2f} "
              f"{jain:>6.3f} {pfc:>6}")


if __name__ == "__main__":
    main()
