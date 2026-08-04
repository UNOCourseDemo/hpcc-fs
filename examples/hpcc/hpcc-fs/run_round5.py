#!/usr/bin/env python3
"""Round-5 review experiments.

A  Fan-in x flow-size matrix (R5-MC1/Q1/Q7): is the ~2x FCT gap at S=64 a
   fixed convergence transient (amortized by larger flows) or persistent
   underutilization? Reports lifetime utilization = serialization bound / FCT.
B  Remaining floor bound (R5-MC2/Q2): N <= C/R_floor = 250 at 100 Mb/s.
   Measure S=256 at floors {100, 50} Mb/s and S=128 at 50 Mb/s.
C  Stock-HPCC parameter sensitivity (R5-MC4/Q4): does the N=4 unfairness
   survive sweeps of u_target (eta), rate_ai, and min_rate?
D  Per-QP fairness amplification (R5 additional #5): job A opens m QPs vs
   job B's one on a shared bottleneck; expect m shares.
E  Wire-overhead calibration (R5-MC3/Q3): solo 50 MB flow FCT vs the
   payload-only bound quantifies the header/serialization share of P_i.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round5.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")
sys.path.insert(0, HERE)
import gen_parking_lot as gpl  # noqa: E402

C_BPS = 25e9


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def sim(base, cfg_extra=None, cfg_replace=None):
    cfgp = os.path.join(HERE, "configs", f"hpcc_{base}.yml")
    if cfg_replace:
        t = open(cfgp).read()
        for old, new in cfg_replace:
            assert old in t, (base, old)
            t = t.replace(old, new, 1)
        open(cfgp, "w").write(t)
    if cfg_extra:
        with open(cfgp, "a") as f:
            f.write(cfg_extra)
    out = os.path.join(HERE, "output", base)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{base}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    assert rc == 0, base
    fcts = {}
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) >= 7:
                fcts.setdefault(ipid(p[0]), []).append(int(p[6]))
    return fcts, pfc_stats(out)


def pfc_stats(out):
    f = os.path.join(out, "pfc.txt")
    if not os.path.exists(f):
        return (0, 0.0)
    open_t, total, count = {}, 0.0, 0
    for ln in open(f):
        p = ln.split()
        t, key, typ = int(p[0]), (p[1], p[2], p[4]), int(p[5])
        if typ == 1:
            open_t[key] = t
            count += 1
        elif key in open_t:
            total += (t - open_t.pop(key)) / 1e3
    return (count, total)


def incast(S, size, cc, floor, tag):
    n_nodes = S + 2
    topo = [f"{n_nodes} 1 {S+1}", "0", "0 1 25Gbps 0.001ms 0"]
    topo += [f"0 {i} 100Gbps 0.001ms 0" for i in range(2, S + 2)]
    flows = [str(S)] + [f"{i} 1 3 100 {size} 0.000000" for i in range(2, S + 2)]
    stop = max(0.1, S * size * 8 / C_BPS * 5)
    gpl.build(1, flow_size=size, stop_time=stop, bn_delay="0.001ms",
              has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=cc)
    base = f"parking_lot_1bn_{tag}"
    with open(os.path.join(HERE, "topologies", f"{base}.txt"), "w") as fh:
        fh.write("\n".join(topo) + "\n")
    with open(os.path.join(HERE, "flows", f"{base}.txt"), "w") as fh:
        fh.write("\n".join(flows) + "\n")
    with open(os.path.join(HERE, "traces", f"{base}_nodes.txt"), "w") as fh:
        fh.write(f"{n_nodes}\n" + " ".join(str(i) for i in range(n_nodes)) + "\n")
    extra = f"fs_min_rate: {floor}\n" if floor else None
    f, pfc = sim(base, cfg_extra=extra)
    all_f = [v for vs in f.values() for v in vs]
    assert len(all_f) == S, (base, len(all_f))
    mean_us = sum(all_f) / len(all_f) / 1e3
    bound_us = S * size * 8 / C_BPS * 1e6
    return mean_us, bound_us, pfc


def part_a():
    print("== A. fan-in x size matrix: lifetime utilization = bound/FCT ==")
    print(f"  {'S':>4} {'size':>6} {'scheme':>6} {'mean FCT us':>11} {'bound us':>9} "
          f"{'util':>5} {'impl Mb/s':>9} {'PFC':>5}")
    cases = [(32, 200_000), (64, 200_000), (128, 200_000),
             (64, 1_000_000), (64, 10_000_000), (64, 50_000_000)]
    for S, size in cases:
        for cc, lab in ((3, "HPCC"), (11, "RCP")):
            floor = "100Mb/s" if cc == 11 else None
            tag = f"r5a{S}_{size//1000}k_{lab}"
            mean_us, bound_us, (n, tot) = incast(S, size, cc, floor, tag)
            print(f"  {S:>4} {size//1000:>5}K {lab:>6} {mean_us:>11.0f} {bound_us:>9.0f} "
                  f"{bound_us/mean_us:>5.2f} {size*8/mean_us/1e3:>9.0f} {n:>5}")


def part_b():
    print("== B. remaining floor bound: N <= C/R_floor (250 at 100M, 500 at 50M) ==")
    print(f"  {'S':>4} {'floor':>8} {'mean FCT us':>11} {'util':>5} {'PFC':>5} {'paused us':>10}")
    for S, floor in ((128, "50Mb/s"), (256, "100Mb/s"), (256, "50Mb/s")):
        tag = f"r5b{S}_{floor.replace('/','')}"
        mean_us, bound_us, (n, tot) = incast(S, 200_000, 11, floor, tag)
        print(f"  {S:>4} {floor:>8} {mean_us:>11.0f} {bound_us/mean_us:>5.2f} {n:>5} {tot:>10.1f}")


def part_c():
    print("== C. stock HPCC parameter sensitivity, N=4 parking lot ==")
    print(f"  {'variant':<28} {'unfairness':>10} {'PFC':>5}")
    sweeps = [("reference (eta .95, ai 40M)", []),
              ("eta 0.90", [("u_target: 0.95", "u_target: 0.90")]),
              ("eta 0.98", [("u_target: 0.95", "u_target: 0.98")]),
              ("rate_ai 200M", [("rate_ai: 40Mb/s", "rate_ai: 200Mb/s")]),
              ("rate_ai 1G", [("rate_ai: 40Mb/s", "rate_ai: 1000Mb/s")]),
              ("min_rate 100M", [("min_rate: 1000Mb/s", "min_rate: 100Mb/s")]),
              ("eta .98 + ai 1G", [("u_target: 0.95", "u_target: 0.98"),
                                   ("rate_ai: 40Mb/s", "rate_ai: 1000Mb/s")])]
    for lab, repl in sweeps:
        tag = "r5c" + re.sub(r"[^a-z0-9]", "", lab.lower())[:16]
        gpl.build(4, flow_size=50_000_000, stop_time=0.4, bn_delay="0.002ms",
                  has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=3)
        f, (n, _) = sim(f"parking_lot_4bn_{tag}", cfg_replace=repl or None)
        lo = f[5][0]
        cr = [v[0] for k, v in f.items() if k != 5]
        print(f"  {lab:<28} {lo/(sum(cr)/len(cr)):>9.3f}x {n:>5}")


def part_d():
    print("== D. per-QP amplification: job A = 2 QPs vs job B = 1 QP, one bottleneck ==")
    gpl.build(1, flow_size=50_000_000, stop_time=0.3, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_r5qp", cc_mode=11)
    lines = ["3", "2 3 3 100 50000000 0.000000", "2 3 3 100 50000000 0.000000",
             "4 5 3 100 50000000 0.000000"]
    with open(os.path.join(HERE, "flows", "parking_lot_1bn_r5qp.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    f, (n, _) = sim("parking_lot_1bn_r5qp")
    a = sorted(f[2])
    b = f[4][0]
    # job completion = when its last byte lands; per-QP rates from FCTs
    ra = [50e6 * 8 / x / 1e3 for x in a]   # Mb/s per QP of job A
    rb = 50e6 * 8 / b / 1e3
    print(f"  job A (2 QPs): per-QP FCTs {a[0]/1e6:.1f}/{a[1]/1e6:.1f} ms "
          f"(rates {ra[0]:.0f}/{ra[1]:.0f} Mb/s)")
    print(f"  job B (1 QP):  FCT {b/1e6:.1f} ms (rate {rb:.0f} Mb/s)")
    print(f"  job-level share ratio A:B = {(ra[0]+ra[1])/rb:.2f} (per-QP fairness, PFC {n})")


def part_e():
    print("== E. wire-overhead calibration: solo 50 MB flow vs payload-only bound ==")
    gpl.build(1, flow_size=50_000_000, stop_time=0.3, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_r5solo", cc_mode=11)
    lines = ["1", "2 3 3 100 50000000 0.000000"]
    with open(os.path.join(HERE, "flows", "parking_lot_1bn_r5solo.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    f, _ = sim("parking_lot_1bn_r5solo")
    fct = f[2][0] / 1e6
    bound = 50e6 * 8 / C_BPS * 1e3
    print(f"  solo FCT {fct:.2f} ms vs payload bound {bound:.2f} ms -> "
          f"wire+protocol overhead {100*(fct/bound-1):.1f}%")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("parts", nargs="?", default="abcde")
    parts = ap.parse_args().parts
    for name, fn in (("a", part_a), ("b", part_b), ("c", part_c),
                     ("d", part_d), ("e", part_e)):
        if name in parts:
            fn(); print()
