#!/usr/bin/env python3
"""Round-4 review experiments.

A  Decisive rate-floor question (R-MC1/Q1/Q2): with the adopted-rate floor
   decoupled from the 1 Gbps cold-start (fs_min_rate, default 100 Mb/s),
   rerun incast S in {32, 64, 128}. If the S=64 PFC storm was floor-induced
   overload (N*floor > C), it disappears and per-sender implied rate falls
   below 1 Gbps. Also reproduce the old conflated behavior (fs_min_rate =
   1000Mb/s) at S=64 for the before/after row, with PFC pause DURATIONS.
B  Regression gates: N=4 parking-lot cc11 headline and idle-gap probe are
   unchanged by the new floor (it never binds when fair shares >> 100 Mb/s).
C  FQ ablations (R-MC2/Q3): per-flow DRR + stock HPCC senders with
   (i) NIC-scaled var_win, (ii) no window at all, (iii) fixed maxBDP window.
   If all fail alike, the confound (window underfeeding vs signal placement)
   is resolved: the port-global INT signal, not the window, is binding.
D  k=6 saturating equal-header control (R-MC4/Q4): cc_mode 12 all-FS (42-byte
   stock INT layout) on the 108-flow workload, plus fluid ideal-balance bound.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round4.py
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
import gen_fattree as gf       # noqa: E402


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def sim(base, cfg_extra=None):
    if cfg_extra:
        with open(os.path.join(HERE, "configs", f"hpcc_{base}.yml"), "a") as f:
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
    """(pause_count, total_pause_us, max_pause_us) from pause/resume pairs."""
    f = os.path.join(out, "pfc.txt")
    if not os.path.exists(f):
        return (0, 0.0, 0.0)
    open_t, total, mx, count = {}, 0.0, 0.0, 0
    for ln in open(f):
        p = ln.split()
        t, key, typ = int(p[0]), (p[1], p[2], p[4]), int(p[5])
        if typ == 1:
            open_t[key] = t
            count += 1
        elif key in open_t:
            d = (t - open_t.pop(key)) / 1e3
            total += d
            mx = max(mx, d)
    return (count, total, mx)


def incast(S, cc, mr, floor, tag):
    n_nodes = S + 2
    topo = [f"{n_nodes} 1 {S+1}", "0", "0 1 25Gbps 0.001ms 0"]
    topo += [f"0 {i} 100Gbps 0.001ms 0" for i in range(2, S + 2)]
    flows = [str(S)] + [f"{i} 1 3 100 200000 0.000000" for i in range(2, S + 2)]
    gpl.build(1, flow_size=200_000, stop_time=0.1, bn_delay="0.001ms",
              has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=cc, min_rate=mr)
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
    mean_ms = sum(all_f) / len(all_f) / 1e6
    # implied per-sender steady rate from the mean FCT (Mbps)
    implied = 200_000 * 8 / (sum(all_f) / len(all_f)) * 1e3
    return mean_ms, max(all_f) / 1e6, implied, pfc


def part_a():
    print("== A. rate floor decoupled: incast sweep (fair share at S=64 is 0.39G < 1G start) ==")
    print(f"  {'S':>4} {'scheme/floor':>22} {'mean ms':>8} {'max ms':>7} "
          f"{'implied Mb/s':>12} {'PFC':>5} {'pause tot us':>12} {'max us':>7}")
    for S in (32, 64, 128):
        rows = [(3, "1000Mb/s", None, f"HPCC"),
                (11, "1000Mb/s", "100Mb/s", "RCP floor 100M")]
        if S == 64:
            rows.append((11, "1000Mb/s", "1000Mb/s", "RCP floor=start 1G"))
        for cc, mr, floor, lab in rows:
            tag = f"r4in{S}_{lab.replace(' ','').replace('=','').replace('/','')}"
            mean_ms, max_ms, implied, (n, tot, mx) = incast(S, cc, mr, floor, tag)
            print(f"  {S:>4} {lab:>22} {mean_ms:>8.2f} {max_ms:>7.2f} "
                  f"{implied:>12.0f} {n:>5} {tot:>12.1f} {mx:>7.1f}")


def part_b():
    print("== B. regression gates with the new 100 Mb/s floor ==")
    gpl.build(4, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_r4gate", cc_mode=11)
    f, (n, tot, mx) = sim("parking_lot_4bn_r4gate")
    lo = f[5][0]
    cr = [v[0] for k, v in f.items() if k != 5]
    print(f"  N=4 headline: unfairness {lo/(sum(cr)/len(cr)):.3f}x  PFC {n}")
    gpl.build(1, flow_size=10_000_000, stop_time=0.4, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_r4idle", cc_mode=11)
    lines = ["5", "2 3 3 100 10000000 0.000000", "4 5 3 100 10000000 0.000000",
             "2 3 3 100 10000000 0.000000", "4 5 3 100 10000000 0.000000",
             "2 3 3 100 1000000 0.114700"]
    with open(os.path.join(HERE, "flows", "parking_lot_1bn_r4idle.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    f, (n, _, _) = sim("parking_lot_1bn_r4idle")
    print(f"  idle-gap 100ms probe: {sorted(f[2])[0]/1e6:.3f} ms  PFC {n}")


def part_c():
    print("== C. FQ ablations: per-flow DRR + stock HPCC senders, window variants ==")
    for has_win, var_win, lab in ((1, "true", "NIC-scaled var_win"),
                                  (0, "false", "no window"),
                                  (1, "false", "fixed maxBDP window")):
        tag = f"r4fq{has_win}{var_win[0]}"
        gpl.build(4, flow_size=50_000_000, stop_time=1.5, bn_delay="0.002ms",
                  has_win=has_win, var_win=var_win, suffix=f"_{tag}", cc_mode=3)
        lines = ["5", "5 6 1 100 50000000 0.000000", "7 8 2 100 50000000 0.000000",
                 "9 10 3 100 50000000 0.000000", "11 12 4 100 50000000 0.000000",
                 "13 14 5 100 50000000 0.000000"]
        with open(os.path.join(HERE, "flows", f"parking_lot_4bn_{tag}.txt"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
        extra = "dwrr_weights:\n" + "".join(f"  {i}: 1.0\n" for i in range(1, 6))
        f, (n, _, _) = sim(f"parking_lot_4bn_{tag}", cfg_extra=extra)
        lo = f[5][0]
        cr = [v[0] for k, v in f.items() if k != 5]
        print(f"  DRR + {lab:<22}: unfairness {lo/(sum(cr)/len(cr)):.3f}x  PFC {n}")


def part_d():
    print("== D. k=6 saturating: equal-header control + fluid ideal-balance bound ==")
    K, SIZE = 6, 20_000_000
    N_HOST = K * (K // 2) ** 2
    HOST0 = (K // 2) ** 2 + 2 * K * (K // 2)
    bound_ms = N_HOST * 2 // (2 * 9) * SIZE * 8 / 25e9 * 1e3 / 3  # 18 flows over 9 uplinks*25G per pod
    # per-pod: 18 flows x 20MB over 225 Gbps = 12.8 ms fluid drain
    bound_ms = 18 * SIZE * 8 / 225e9 * 1e3
    print(f"  fluid ideal-balance bound (perfect ECMP): {bound_ms:.1f} ms")
    for cc, extra, lab in ((3, None, "HPCC (42B INT)"),
                           (11, None, "RDMA-RCP (8B field)"),
                           (12, "mix_fs_dport: 1\n", "RDMA-RCP (42B padded)")):
        name = f"ft6_r4_cc{cc}"
        gf.build(name, k=K, cc_mode=cc, flow_size=SIZE, stop=0.3)
        flows = [str(2 * N_HOST)]
        for i in range(N_HOST):
            for off in (9, 27):
                flows.append(f"{HOST0+i} {HOST0+(i+off)%N_HOST} 3 100 {SIZE} 0.000000")
        with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as fh:
            fh.write("\n".join(flows) + "\n")
        f, (n, tot, mx) = sim(name, cfg_extra=extra)
        fcts = [v for vs in f.values() for v in vs]
        jain = sum(fcts) ** 2 / (len(fcts) * sum(x * x for x in fcts))
        mk = max(fcts) / 1e6
        print(f"  {lab:<24}: makespan {mk:6.2f} ms ({mk/bound_ms:.2f}x bound)  "
              f"mean {sum(fcts)/len(fcts)/1e6:6.2f}  Jain {jain:.3f}  PFC {n}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("parts", nargs="?", default="abcd")
    parts = ap.parse_args().parts
    if "a" in parts: part_a(); print()
    if "b" in parts: part_b(); print()
    if "c" in parts: part_c(); print()
    if "d" in parts: part_d()
