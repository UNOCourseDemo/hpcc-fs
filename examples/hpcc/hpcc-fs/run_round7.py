#!/usr/bin/env python3
"""Enhancement round 7: multi-phase collective + a positive deployment workload.

M  Chained multi-phase ring collective (R5-MC3 follow-through): four
   barrier-synchronized phases of a chunked ring allreduce (50 MB / 16 hosts
   = 3.125 MB per chunk), simulated iteratively -- phase p+1's flows start at
   phase p's MEASURED completion, and each iteration replays the full history
   so controller state carries across phases. Verifies that absolute per-phase
   savings accumulate (and that no cross-phase pathology appears).

W  A composite "training-like" service on the k=4 fat-tree, entirely on one
   mode: ring coflow (16 x 20 MB) + a 15-to-1 parameter-server incast (200 KB,
   t=5 ms) + 32 short 64 KB RPCs (staggered). Answers R5-MC8's "what realistic
   service can be assigned entirely to RDMA-RCP?" with per-class metrics.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round7.py
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

RING = J.RING                  # 16 (src, dst) host-id pairs
CHUNK = 3_125_000              # 50 MB / 16 chunks
N_PHASES = 4


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


def read_fct_rows(out):
    rows = []
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) >= 7:
                rows.append((ipid(p[0]), ipid(p[1]), int(p[5]), int(p[6])))
    return rows  # (src, dst, start_ns, fct_ns)


def pfc_count(out):
    f = os.path.join(out, "pfc.txt")
    return sum(1 for ln in open(f) if ln.split()[5] == "1") if os.path.exists(f) else 0


def part_m():
    print(f"== M. chained ring collective: {N_PHASES} barrier-synchronized "
          f"{CHUNK//1000} KB phases ==")
    single = {}
    for cc, lab in ((3, "HPCC"), (11, "RDMA-RCP")):
        starts = [0.0]
        for phase in range(1, N_PHASES + 1):
            name = f"ft4_r7m_cc{cc}"
            g4.build(name, cc_mode=cc, stop=starts[-1] + 0.1)
            flows = [str(16 * phase)]
            for p, t in enumerate(starts[:phase]):
                for (s, d) in RING:
                    flows.append(f"{s} {d} 3 100 {CHUNK} {t:.6f}")
            with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as fh:
                fh.write("\n".join(flows) + "\n")
            out = run_sim(name)
            rows = read_fct_rows(out)
            t_ns = round(starts[-1] * 1e9)
            phase_rows = [r for r in rows if abs(r[2] - t_ns) < 1000]
            assert len(phase_rows) == 16, (cc, phase, len(phase_rows))
            done = max(r[2] + r[3] for r in phase_rows) / 1e9
            starts.append(done)
        jcts = [(starts[i + 1] - starts[i]) * 1e3 for i in range(N_PHASES)]
        total = (starts[-1] - starts[0]) * 1e3
        single[cc] = (jcts, total, pfc_count(out))
        print(f"  {lab:>9}: per-phase JCT [{', '.join(f'{j:.2f}' for j in jcts)}] ms  "
              f"total {total:.2f} ms  PFC {single[cc][2]}")
    tot3, tot11 = single[3][1], single[11][1]
    print(f"  chained 4-phase gain: {100*(tot3-tot11)/tot3:.1f}% "
          f"(single-phase gain at this chunk size: {100*(single[3][0][0]-single[11][0][0])/single[3][0][0]:.1f}%)")


def part_w():
    print("== W. composite training-like service on k=4 fat-tree, one mode ==")
    # classes: ring coflow (16 x 20 MB, t=0); PS incast 15 -> host 20 (200 KB,
    # t=5 ms); 32 RPCs (64 KB) staggered 0..8 ms, deterministic pairs
    hosts = J.HOSTS
    rpc = [(hosts[i % 16], hosts[(i + 5) % 16], i * 0.25e-3) for i in range(32)]
    print(f"  {'':>10} {'coflow JCT ms':>13} {'incast mean us':>14} "
          f"{'RPC mean us':>11} {'PFC':>5}")
    for cc, lab in ((3, "HPCC"), (11, "RDMA-RCP")):
        name = f"ft4_r7w_cc{cc}"
        g4.build(name, cc_mode=cc, stop=0.15)
        flows = []
        for (s, d) in RING:
            flows.append(f"{s} {d} 3 100 20000000 0.000000")
        for h in hosts:
            if h != 20:
                flows.append(f"{h} 20 3 100 200000 0.005000")
        for (s, d, t) in rpc:
            if s != d:
                flows.append(f"{s} {d} 3 100 64000 {t:.6f}")
        flows.sort(key=lambda ln: float(ln.split()[5]))  # harness needs sorted starts
        with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as fh:
            fh.write(f"{len(flows)}\n" + "\n".join(flows) + "\n")
        out = run_sim(name)
        rows = read_fct_rows(out)
        ring_set = {(s, d) for (s, d) in RING}
        cof = [r[3] for r in rows if (r[0], r[1]) in ring_set and r[2] == 0]
        inc = [r[3] for r in rows if r[1] == 20 and abs(r[2] - 5_000_000) < 1000]
        rpcf = [r[3] for r in rows if r[3] and 0 < r[2] < 8_100_000
                and abs(r[2] - 5_000_000) >= 1000 and (r[0], r[1]) not in ring_set]
        rpcf = rpcf or [r[3] for r in rows if (r[0], r[1]) not in ring_set
                        and abs(r[2] - 5_000_000) >= 1000]
        assert len(cof) == 16 and len(inc) == 15, (len(cof), len(inc), len(rpcf))
        print(f"  {lab:>10} {max(cof)/1e6:>13.2f} {sum(inc)/len(inc)/1e3:>14.1f} "
              f"{sum(rpcf)/len(rpcf)/1e3:>11.1f} {pfc_count(out)}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("parts", nargs="?", default="mw")
    parts = ap.parse_args().parts
    if "m" in parts: part_m(); print()
    if "w" in parts: part_w()
