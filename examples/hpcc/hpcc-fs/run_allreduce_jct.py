#!/usr/bin/env python3
"""Allreduce-style coflow JCT on the k=4 fat-tree (review response: real-workload value).

A collective step completes when its SLOWEST flow completes: JCT = max FCT
over the coflow. Cross-pod ring segments are multi-bottleneck (5-switch
paths); under stock HPCC they are starved and gate the job, while HPCC-FS
equalizes them. Two workloads, both deterministic, swept over 5 ECMP hash
seeds (additive ecmp_seed_offset knob):

  ring   : 16-flow ring allreduce chunk exchange over all hosts in id order
           (4 inter-pod + 4 intra-pod-diff-edge + 8 same-edge flows, 50 MB each).
  ringbg : same ring + 8 short background flows (2 MB, one per pod-edge pair)
           to expose the short-flow cost alongside the JCT gain.

Run from the repo root:
    venv/bin/python examples/hpcc/hpcc-fs/run_allreduce_jct.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")

sys.path.insert(0, HERE)
import gen_fattree_k4 as g4  # noqa: E402

SEEDS = [0, 101, 202, 303, 404]
HOSTS = list(range(20, 36))
RING = [(HOSTS[i], HOSTS[(i + 1) % 16]) for i in range(16)]          # 50 MB each
BG = [(20 + 4 * p + 2 * e, 23 + 4 * p - 2 * e) for p in range(4)     # 2 MB each,
      for e in range(2)]                                             # intra-pod diff-edge
RING_SZ, BG_SZ = 50_000_000, 2_000_000


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def write_flows(name, with_bg):
    flows = [(s, d, RING_SZ) for (s, d) in RING]
    if with_bg:
        flows += [(s, d, BG_SZ) for (s, d) in BG]
    lines = [str(len(flows))] + [f"{s} {d} 3 100 {sz} 0.000000" for (s, d, sz) in flows]
    with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


def run(name, cc, seed, with_bg):
    g4.build(name, cc_mode=cc)               # topo + config skeleton
    write_flows(name, with_bg)               # replace workload with the ring
    if seed != 0:
        with open(os.path.join(HERE, "configs", f"hpcc_{name}.yml"), "a") as f:
            f.write(f"ecmp_seed_offset: {seed}\n")
    out = os.path.join(HERE, "output", name)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(f"{name} exit {rc}")
    ring_set = {(s, d) for (s, d) in RING}
    ring_f, bg_f = [], []
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) < 7:
                continue
            key = (ipid(p[0]), ipid(p[1]))
            (ring_f if key in ring_set else bg_f).append(int(p[6]))
    nexp = 16 + (8 if with_bg else 0)
    assert len(ring_f) == 16 and len(ring_f) + len(bg_f) == nexp, \
        f"{name}: {len(ring_f)} ring / {len(bg_f)} bg flows"
    jct = max(ring_f) / 1e6
    bg_mean = (sum(bg_f) / len(bg_f) / 1e6) if bg_f else float("nan")
    return jct, bg_mean


def sweep(tag, with_bg):
    print(f"\n== {tag}: 16-flow ring allreduce{' + 8 short background' if with_bg else ''} ==")
    hdr = f"{'seed':>5} | {'JCT stock':>10} | {'JCT FS':>8} | {'ΔJCT':>7}"
    if with_bg:
        hdr += f" | {'bg stock':>9} | {'bg FS':>7}"
    print(hdr)
    impr = []
    for s in SEEDS:
        j3, b3 = run(f"ft4_{tag}_cc3_s{s}", 3, s, with_bg)
        j11, b11 = run(f"ft4_{tag}_cc11_s{s}", 11, s, with_bg)
        d = (j3 - j11) / j3 * 100
        impr.append(d)
        row = f"{s:>5} | {j3:>8.2f}ms | {j11:>6.2f}ms | {d:>+6.1f}%"
        if with_bg:
            row += f" | {b3:>7.2f}ms | {b11:>5.2f}ms"
        print(row)
    print(f"   JCT improvement: min {min(impr):+.1f}%, mean {sum(impr)/len(impr):+.1f}%, "
          f"max {max(impr):+.1f}%")


if __name__ == "__main__":
    sweep("ring", with_bg=False)
    sweep("ringbg", with_bg=True)
