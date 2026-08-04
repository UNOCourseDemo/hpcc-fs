#!/usr/bin/env python3
"""Round-3 review experiments.

E2  idle-gap stale-rate: congest a port, let it idle g in {0.1,1,10,100} ms,
    then a single 1 MB flow arrives -- does it inherit a stale low R?
E3  header-size control: ring-allreduce JCT with the FS class padded to the
    stock 42-byte INT layout (cc_mode 12, all-FS) vs stock HPCC.
E4  per-flow fair-queueing baseline: stock HPCC senders + per-flow queues +
    equal-weight DRR at every switch port (uses existing dwrr_weights).
E5  incast fan-in sweep: S in {3,8,16,32,64} senders x startup {1,8} Gbps.
E7  joint stress: churn + d/4 + RTT spread simultaneously, RCP mode.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round3.py
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
import gen_fattree_k4 as g4    # noqa: E402


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
    pfcf = os.path.join(out, "pfc.txt")
    pfc = sum(1 for _ in open(pfcf)) if os.path.exists(pfcf) else 0
    return fcts, pfc


def e2_idle_gap():
    print("== E2 idle-gap stale rate (cc11): 4x10MB congest, idle g, then 1MB probe ==")
    # solo baseline: probe alone on fresh port
    gpl.build(1, flow_size=1_000_000, stop_time=0.3, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_solo", cc_mode=11)
    f, _ = sim("parking_lot_1bn_solo")
    solo = f[2][0] / 1e6
    print(f"  fresh-port 1MB solo: {solo:.3f} ms")
    for g_ms in (0.1, 1.0, 10.0, 100.0):
        tag = f"idle{str(g_ms).replace('.','p')}"
        gpl.build(1, flow_size=10_000_000, stop_time=0.4, bn_delay="0.002ms",
                  has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=11)
        # 4 congesting flows share the single bottleneck (all from long side +
        # cross side), then the probe (from long src) after estimated drain+gap.
        # Congesters: 4 x 10MB from 4 host pairs; probe 1MB at t_probe.
        # n=1 topo has hosts: long 2->3, cross 4->5. Add congesters via repeated
        # flows on the same two host pairs (dports differ automatically).
        drain = 4 * 10_000_000 * 8 / 25e9 * 1.15  # ~14.7ms with margin
        t_probe = drain + g_ms / 1e3
        lines = ["5",
                 f"2 3 3 100 10000000 0.000000",
                 f"4 5 3 100 10000000 0.000000",
                 f"2 3 3 100 10000000 0.000000",
                 f"4 5 3 100 10000000 0.000000",
                 f"2 3 3 100 1000000 {t_probe:.6f}"]
        with open(os.path.join(HERE, "flows", f"parking_lot_1bn_{tag}.txt"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
        f, pfc = sim(f"parking_lot_1bn_{tag}")
        # probe = smallest FCT among src-2 flows (the 1 MB finishes fastest)
        probe = sorted(f[2])[0] / 1e6
        print(f"  idle gap {g_ms:>6.1f} ms: probe FCT {probe:.3f} ms "
              f"({probe/solo:.2f}x solo)  PFC {pfc}")


def e3_header_control():
    print("== E3 header-size control: ring JCT, FS padded to stock 42B (cc12 all-FS) ==")
    import run_allreduce_jct as J
    for cc, extra, lab in ((3, None, "stock HPCC (42B INT)"),
                           (11, None, "RDMA-RCP (8B field)"),
                           (12, "mix_fs_dport: 1\n", "RDMA-RCP (42B padded)")):
        name = f"ft4_hdr_cc{cc}"
        g4.build(name, cc_mode=cc)
        J.write_flows(name, False)
        if extra:
            with open(os.path.join(HERE, "configs", f"hpcc_{name}.yml"), "a") as fh:
                fh.write(extra)
        out = os.path.join(HERE, "output", name)
        os.makedirs(out, exist_ok=True)
        for fn in os.listdir(out):
            os.remove(os.path.join(out, fn))
        with open(os.path.join(out, "sim.log"), "w") as log:
            rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                                stdout=log, stderr=subprocess.STDOUT).returncode
        assert rc == 0, name
        ring = {(s, d) for (s, d) in J.RING}
        fs = []
        with open(os.path.join(out, "fct.txt")) as fh:
            for ln in fh:
                p = ln.split()
                if len(p) >= 7 and (ipid(p[0]), ipid(p[1])) in ring:
                    fs.append(int(p[6]))
        print(f"  {lab:<24}: JCT {max(fs)/1e6:.2f} ms")


def e4_fq_baseline():
    print("== E4 per-flow FQ baseline: stock HPCC senders + per-flow DRR queues ==")
    for cc, lab in ((3, "stock HPCC + per-flow DRR"), (11, "RDMA-RCP (no FQ)")):
        tag = f"fq{cc}"
        gpl.build(4, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
                  has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=cc)
        if cc == 3:
            # one pg per flow (1..5) => per-flow queues; DRR equal weights
            lines = ["5",
                     "5 6 1 100 50000000 0.000000",
                     "7 8 2 100 50000000 0.000000",
                     "9 10 3 100 50000000 0.000000",
                     "11 12 4 100 50000000 0.000000",
                     "13 14 5 100 50000000 0.000000"]
            with open(os.path.join(HERE, "flows", f"parking_lot_4bn_{tag}.txt"), "w") as fh:
                fh.write("\n".join(lines) + "\n")
            extra = "dwrr_weights:\n" + "".join(f"  {i}: 1.0\n" for i in range(1, 6))
        else:
            extra = None
        f, pfc = sim(f"parking_lot_4bn_{tag}", cfg_extra=extra)
        lo = f[5][0]
        cr = [v[0] for k, v in f.items() if k != 5]
        print(f"  {lab:<28}: unfairness {lo/(sum(cr)/len(cr)):.3f}x  PFC {pfc}")


def e5_incast():
    print("== E5 incast fan-in sweep: S senders -> 1 receiver, 200KB each ==")
    print(f"  {'S':>4} {'scheme':>16} {'mean FCT us':>12} {'max FCT us':>11} {'PFC':>5}")
    for S in (3, 8, 16, 32, 64):
        # star: switch 0; receiver host 1 (25G link); senders 2..S+1 (100G)
        n_nodes = S + 2
        topo = [f"{n_nodes} 1 {S+1}", "0", "0 1 25Gbps 0.001ms 0"]
        topo += [f"0 {i} 100Gbps 0.001ms 0" for i in range(2, S + 2)]
        flows = [str(S)] + [f"{i} 1 3 100 200000 0.000000" for i in range(2, S + 2)]
        for cc, mr, lab in ((3, "1000Mb/s", "HPCC"),
                            (11, "1000Mb/s", "RCP start1G"),
                            (11, "8000Mb/s", "RCP start8G")):
            tag = f"incast{S}_{lab.replace(' ','')}"
            gpl.build(1, flow_size=200_000, stop_time=0.05, bn_delay="0.001ms",
                      has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=cc,
                      min_rate=mr)
            base = f"parking_lot_1bn_{tag}"
            with open(os.path.join(HERE, "topologies", f"{base}.txt"), "w") as fh:
                fh.write("\n".join(topo) + "\n")
            with open(os.path.join(HERE, "flows", f"{base}.txt"), "w") as fh:
                fh.write("\n".join(flows) + "\n")
            with open(os.path.join(HERE, "traces", f"{base}_nodes.txt"), "w") as fh:
                fh.write(f"{n_nodes}\n" + " ".join(str(i) for i in range(n_nodes)) + "\n")
            f, pfc = sim(base)
            all_f = [v for vs in f.values() for v in vs]
            print(f"  {S:>4} {lab:>16} {sum(all_f)/len(all_f)/1e3:>12.1f} "
                  f"{max(all_f)/1e3:>11.1f} {pfc:>5}")


def e7_joint():
    print("== E7 joint stress: churn + RTT spread + d/4, RCP mode ==")
    import run_stress_matrix as M
    base, fd, ss, caps = M.build_scenario(
        "joint", [25, 25, 25, 25], [0, 0, 0, 0],
        [(0, 3, 100_000_000, 0.0)],
        [(0, 25_000_000, 0.000), (1, 25_000_000, 0.010),
         (2, 25_000_000, 0.020), (3, 25_000_000, 0.030),
         (0, 25_000_000, 0.040), (2, 25_000_000, 0.050)],
        cc_mode=11)
    # overwrite topology delays for RTT spread: bn 0.008ms, keep host 0.001
    tp = os.path.join(HERE, "topologies", f"{base}.txt")
    t = open(tp).read().replace("0.002ms", "0.008ms")
    open(tp, "w").write(t)
    with open(os.path.join(HERE, "configs", f"hpcc_{base}.yml"), "a") as fh:
        fh.write("fs_d_scale: 0.25\n")
    st = M.penalty(base, fd, ss, caps, [0])
    print(f"  RCP joint-stress: unfairness {st['unf']:.3f}x  "
          f"P[{st['pmin']:.2f},{st['pmean']:.2f},{st['pmax']:.2f}]  util {st['util']:.2f}")


if __name__ == "__main__":
    e2_idle_gap()
    print()
    e3_header_control()
    print()
    e4_fq_baseline()
    print()
    e5_incast()
    print()
    e7_joint()
