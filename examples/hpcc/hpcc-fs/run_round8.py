#!/usr/bin/env python3
"""Round-6 review (Weak Accept -> Accept path).

D  The d = 2 x RTT_max operating point (reviewer's "highest-value remaining
   experiment"): repeat the compact key-workload set under fs_d_scale = 2 --
   headline N=4, small-long-flow worst case, churn (S4), ring coflow,
   64-way and 128-way fan-in. One table answers Q1/Q3.
P  Full 30-phase ring allreduce (2(N-1) phases for N=16), barrier-chained
   iteratively with controller state carried -- eliminates the partial-
   collective objection (Q4) entirely.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round8.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")
sys.path.insert(0, HERE)
import gen_parking_lot as gpl   # noqa: E402
import gen_fattree_k4 as g4     # noqa: E402
import run_allreduce_jct as J   # noqa: E402
import run_stress_matrix as M   # noqa: E402

C_BPS = 25e9


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


def per_src(out):
    per = {}
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) >= 7:
                per.setdefault(ipid(p[0]), []).append(int(p[6]))
    return per


def pfc_count(out):
    f = os.path.join(out, "pfc.txt")
    return sum(1 for ln in open(f) if ln.split()[5] == "1") if os.path.exists(f) else 0


def add_d2(base):
    with open(os.path.join(HERE, "configs", f"hpcc_{base}.yml"), "a") as fh:
        fh.write("fs_d_scale: 2\n")


def incast_d2(S, size, tag):
    n_nodes = S + 2
    stop = max(0.1, S * size * 8 / C_BPS * 6)
    gpl.build(1, flow_size=size, stop_time=stop, bn_delay="0.001ms",
              has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=11)
    base = f"parking_lot_1bn_{tag}"
    topo = [f"{n_nodes} 1 {S+1}", "0", "0 1 25Gbps 0.001ms 0"]
    topo += [f"0 {i} 100Gbps 0.001ms 0" for i in range(2, S + 2)]
    with open(os.path.join(HERE, "topologies", f"{base}.txt"), "w") as fh:
        fh.write("\n".join(topo) + "\n")
    flows = [str(S)] + [f"{i} 1 3 100 {size} 0.000000" for i in range(2, S + 2)]
    with open(os.path.join(HERE, "flows", f"{base}.txt"), "w") as fh:
        fh.write("\n".join(flows) + "\n")
    with open(os.path.join(HERE, "traces", f"{base}_nodes.txt"), "w") as fh:
        fh.write(f"{n_nodes}\n" + " ".join(str(i) for i in range(n_nodes)) + "\n")
    add_d2(base)
    out = run_sim(base)
    fcts = [v for vs in per_src(out).values() for v in vs]
    assert len(fcts) == S
    return (S * size * 8 / C_BPS * 1e9) / (sum(fcts) / len(fcts)), pfc_count(out)


def part_d():
    print("== D. one operating point: every key workload at d = 2 x RTT_max ==")
    # 1. headline N=4 (d1 ref: 1.005x, PFC 0)
    gpl.build(4, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_r8d2", cc_mode=11)
    add_d2("parking_lot_4bn_r8d2")
    out = run_sim("parking_lot_4bn_r8d2")
    per = per_src(out)
    lo = per[5][0]; cr = [v[0] for k, v in per.items() if k != 5]
    print(f"  headline N=4        : {lo/(sum(cr)/len(cr)):.3f}x  PFC {pfc_count(out)}  (d1: 1.005x)")
    # 2. small long flow (stock worst case 3.53x; d1 RCP: 1.012x)
    gpl.build(4, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_r8d2s", cc_mode=11,
              long_size=2_000_000)
    add_d2("parking_lot_4bn_r8d2s")
    out = run_sim("parking_lot_4bn_r8d2s")
    per = per_src(out)
    # small-long penalty vs oracle-style ratio: long slowdown / mean cross slowdown
    lo = per[5][0] / (2_000_000 / 50_000_000)   # normalize by size ratio
    cr = [v[0] for k, v in per.items() if k != 5]
    print(f"  small long (2 MB)   : {lo/(sum(cr)/len(cr)):.3f}x  PFC {pfc_count(out)}  (d1: ~1.012x)")
    # 3. churn (S4; d1 refs: unf 1.002x, P[1.06,1.07,1.13])
    base, fd, ss, caps = M.build_scenario(
        "r8d2c", [25, 25, 25, 25], [0, 0, 0, 0], [(0, 3, 100_000_000, 0.0)],
        [(0, 25_000_000, 0.000), (1, 25_000_000, 0.010), (2, 25_000_000, 0.020),
         (3, 25_000_000, 0.030), (0, 25_000_000, 0.040), (2, 25_000_000, 0.050)],
        cc_mode=11)
    add_d2(base)
    st = M.penalty(base, fd, ss, caps, [0])
    print(f"  churn (S4)          : {st['unf']:.3f}x  P[{st['pmin']:.2f},{st['pmean']:.2f},"
          f"{st['pmax']:.2f}]  (d1: 1.002x, P[1.06,1.07,1.13])")
    # 4. ring coflow (d1 ref: 17.99 ms)
    name = "ft4_r8d2_ring"
    g4.build(name, cc_mode=11)
    J.write_flows(name, False)
    add_d2(name)
    out = run_sim(name)
    ring = {(a, b) for (a, b) in J.RING}
    fs = []
    with open(os.path.join(out, "fct.txt")) as fh:
        for ln in fh:
            p = ln.split()
            if len(p) >= 7 and (ipid(p[0]), ipid(p[1])) in ring:
                fs.append(int(p[6]))
    print(f"  ring coflow JCT     : {max(fs)/1e6:.2f} ms  PFC {pfc_count(out)}  "
          f"(d1: 17.99 ms; stock: 23.27 ms)")
    # 5+6. fan-in 64 and 128 (d1 refs: 0.47 / 0.51)
    for S in (64, 128):
        util, pfc = incast_d2(S, 200_000, f"r8d2f{S}")
        print(f"  fan-in S={S:<3}        : utilization {util:.2f}  PFC {pfc}  "
              f"(d1: {'0.47' if S == 64 else '0.51'})")


def part_p():
    print("== P. full ring allreduce: 30 barrier-chained 3.125 MB phases (2(N-1), N=16) ==")
    res = {}
    for cc, lab in ((3, "HPCC"), (11, "RDMA-RCP")):
        starts = [0.0]
        for phase in range(1, 31):
            name = f"ft4_r8p_cc{cc}"
            g4.build(name, cc_mode=cc, stop=starts[-1] + 0.05)
            flows = [str(16 * phase)]
            for t in starts[:phase]:
                for (s, d) in J.RING:
                    flows.append(f"{s} {d} 3 100 3125000 {t:.6f}")
            with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as fh:
                fh.write("\n".join(flows) + "\n")
            out = run_sim(name)
            t_ns = round(starts[-1] * 1e9)
            done_ns = 0
            with open(os.path.join(out, "fct.txt")) as fh:
                n_seen = 0
                for ln in fh:
                    p = ln.split()
                    if len(p) >= 7 and abs(int(p[5]) - t_ns) < 1000:
                        n_seen += 1
                        done_ns = max(done_ns, int(p[5]) + int(p[6]))
            assert n_seen == 16, (cc, phase, n_seen)
            starts.append(done_ns / 1e9)
        jcts = [(starts[i + 1] - starts[i]) * 1e3 for i in range(30)]
        res[cc] = (starts[-1] * 1e3, min(jcts), max(jcts), pfc_count(out))
        print(f"  {lab:>9}: total {res[cc][0]:.2f} ms over 30 phases  "
              f"per-phase [{res[cc][1]:.2f}..{res[cc][2]:.2f}] ms  PFC {res[cc][3]}")
    print(f"  full-allreduce gain: {100*(res[3][0]-res[11][0])/res[3][0]:.1f}%")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("parts", nargs="?", default="dp")
    parts = ap.parse_args().parts
    if "d" in parts: part_d(); print()
    if "p" in parts: part_p()
