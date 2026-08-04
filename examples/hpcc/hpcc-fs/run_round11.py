#!/usr/bin/env python3
"""Round-9: header control + seed check for the pipelined 30-phase collective.

H  The reviewer's highest-value remaining experiment: repeat the pipelined
   per-rank 30-phase ring with the RCP class padded to stock's 42-byte INT
   layout (cc_mode 12, all-FS). If the equal-header gain stays near the
   8-byte one, the full-collective headline is not a telemetry-size artifact.
S  Seed check: pipelined chains for stock and RDMA-RCP (8 B) at two more
   ECMP seed offsets (101, 202) to show the full-collective gain is not a
   single-placement result.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round11.py
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

RING = J.RING
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


def pipelined(cc, tag, extra=None, seed=None):
    src_of = {i: RING[i][0] for i in range(16)}
    pred = {i: next(j for j in range(16) if RING[j][1] == RING[i][0])
            for i in range(16)}
    starts = [[0.0] * 16]
    done = None
    for phase in range(N_PHASES):
        name = f"ft4_r11_{tag}"
        g4.build(name, cc_mode=cc, stop=max(starts[-1]) + 0.05)
        if extra or seed:
            with open(os.path.join(HERE, "configs", f"hpcc_{name}.yml"), "a") as fh:
                if extra:
                    fh.write(extra)
                if seed:
                    fh.write(f"ecmp_seed_offset: {seed}\n")
        rows = []
        for k in range(phase + 1):
            for i, (s, d) in enumerate(RING):
                rows.append((starts[k][i], f"{s} {d} 3 100 {CHUNK} {starts[k][i]:.9f}"))
        rows.sort(key=lambda r: r[0])
        with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as fh:
            fh.write(f"{len(rows)}\n" + "\n".join(r[1] for r in rows) + "\n")
        out = run_sim(name)
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
        assert all(d is not None for d in done), (tag, phase)
        if phase + 1 < N_PHASES:
            starts.append([max(done[i], done[pred[i]]) for i in range(16)])
    return max(done) * 1e3


def main():
    print("== H. pipelined 30-phase collective: header control (default seed) ==")
    t3 = pipelined(3, "h3")
    t11 = pipelined(11, "h11")
    t12 = pipelined(12, "h12", extra="mix_fs_dport: 1\n")
    print(f"  HPCC (42B)        : {t3:.2f} ms")
    print(f"  RDMA-RCP (8B)     : {t11:.2f} ms  ({100*(t3-t11)/t3:.1f}%)")
    print(f"  RDMA-RCP (42B pad): {t12:.2f} ms  ({100*(t3-t12)/t3:.1f}%)")
    print()
    print("== S. pipelined seed check (8B vs stock) ==")
    for seed in (101, 202):
        a = pipelined(3, f"s3_{seed}", seed=seed)
        b = pipelined(11, f"s11_{seed}", seed=seed)
        print(f"  seed {seed}: HPCC {a:.2f} ms, RDMA-RCP {b:.2f} ms  "
              f"({100*(a-b)/a:.1f}%)")


if __name__ == "__main__":
    main()
