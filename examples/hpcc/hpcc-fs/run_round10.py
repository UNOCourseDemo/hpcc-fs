#!/usr/bin/env python3
"""Pipelined ring allreduce: per-rank dependencies instead of global barriers.

The round-8 reviewer's point: a real ring pipeline gates rank i's step-(k+1)
send on (a) its own step-k completion and (b) receipt of the step-k chunk from
its ring predecessor -- NOT on the globally slowest transfer. Global barriers
convert every local straggler into a fabric-wide stall, which could inflate
the benefit of fixing stragglers.

Here each phase's per-rank start is computed iteratively:
    start_i^{k+1} = max(done_i^k, done_pred(i)^k)
where done = flow start + measured FCT, and every iteration re-simulates the
full history (controller state carried). 30 phases (2(N-1) for N=16 ranks),
3.125 MB chunks, both schemes. Reported next to the barrier-synchronized
variant (run_round8.py), which is the conservative straggler-sensitive bound.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round10.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")
sys.path.insert(0, HERE)
import gen_fattree_k4 as g4    # noqa: E402
import run_allreduce_jct as J  # noqa: E402

RING = J.RING          # 16 (src, dst) pairs; dst is the ring successor
CHUNK = 3_125_000
N_PHASES = 30


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def run_sim(base):
    out = os.path.join(HERE, "output", base)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{base}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    assert rc == 0, base
    return out


def main():
    print(f"== pipelined ring allreduce: {N_PHASES} phases, per-rank dependencies ==")
    # predecessor of rank r (indexed by RING position): pred sends INTO r's src
    src_of = {i: RING[i][0] for i in range(16)}
    pred = {i: next(j for j in range(16) if RING[j][1] == RING[i][0])
            for i in range(16)}
    res = {}
    for cc, lab in ((3, "HPCC"), (11, "RDMA-RCP")):
        starts = [[0.0] * 16]          # starts[k][i] = start of rank i's phase-k send
        done = None
        for phase in range(N_PHASES):
            name = f"ft4_r10p_cc{cc}"
            latest = max(starts[-1])
            g4.build(name, cc_mode=cc, stop=latest + 0.05)
            rows = []
            for k in range(phase + 1):
                for i, (s, d) in enumerate(RING):
                    rows.append((starts[k][i], f"{s} {d} 3 100 {CHUNK} {starts[k][i]:.9f}"))
            rows.sort(key=lambda r: r[0])
            with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as fh:
                fh.write(f"{len(rows)}\n" + "\n".join(r[1] for r in rows) + "\n")
            out = run_sim(name)
            # collect completions of the CURRENT phase (match by start time)
            done = [None] * 16
            with open(os.path.join(out, "fct.txt")) as fh:
                for ln in fh:
                    p = ln.split()
                    if len(p) < 7:
                        continue
                    src, st, fct = ipid(p[0]), int(p[5]), int(p[6])
                    for i in range(16):
                        if src_of[i] == src and abs(st - round(starts[phase][i] * 1e9)) < 1000:
                            done[i] = (st + fct) / 1e9
            assert all(d is not None for d in done), (cc, phase, done)
            if phase + 1 < N_PHASES:
                starts.append([max(done[i], done[pred[i]]) for i in range(16)])
        total = (max(done) - 0.0) * 1e3
        res[cc] = total
        print(f"  {lab:>9}: pipelined completion {total:.2f} ms "
              f"(barrier variant: {'45.04' if cc == 3 else '35.18'} ms)")
    print(f"  pipelined full-allreduce gain: {100*(res[3]-res[11])/res[3]:.1f}% "
          f"(barrier variant: 21.9%)")


if __name__ == "__main__":
    main()
