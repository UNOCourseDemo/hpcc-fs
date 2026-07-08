#!/usr/bin/env python3
"""Mixed-mode coexistence: stock HPCC and HPCC-FS classes sharing the same links.

Implements the deployment the paper describes: one fabric, two service modes selected
per traffic class. cc_mode 12 uses IntHeader::FSMIX -- a wire layout IDENTICAL to stock
HPCC's NORMAL 42-byte INT record, so stock packets are byte-for-byte unchanged -- and
dispatches per packet at the switch (and per QP at the sender) on the UDP destination
port, which stands in for the fabric's class tag. Both classes sit in the SAME priority
queue (pg=3), so they genuinely contend for the same bottleneck links.

Topology: N=4 parking lot. Long flow (5->6) crosses 4 bottlenecks; 4 cross flows each
cross one. Three configurations:

  all-stock   cc_mode 3            reference: the winner-take-all collapse
  all-fs      cc_mode 11           reference: max-min restored
  mixed       cc_mode 12           long flow -> FS class (dport 200)
                                   cross flows -> stock class (dport 100)

Regression gates run first (both must pass or the experiment is meaningless):
  G1  cc_mode 12 with mix_fs_dport=65535 (every flow is stock class) must reproduce
      cc_mode 3's fct.txt EXACTLY -> proves the stock path is untouched under FSMIX.
  G2  cc_mode 12 with mix_fs_dport=1 (every flow is FS class) must match cc_mode 11's
      fairness (not byte-identical: in FSMIX the FS class carries the 42-byte INT record
      rather than its native 8-byte one, so it pays MORE header overhead -- conservative
      for our claim).

Run from the repo root:
    venv/bin/python examples/hpcc/hpcc-fs/run_mixed_mode.py
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

N = 4
LONG_SRC, LONG_DST = N + 1, N + 2          # 5 -> 6
FS_DPORT = 200                              # dport >= this  => HPCC-FS class
LINE_C = 25e9                               # bottleneck capacity (bits/s)
FAIR = LINE_C / (N + 1) if False else LINE_C / 2.0   # long+1 cross per link => C/2 each


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def write_flows(name, fs_long):
    """Long flow first. fs_long=True -> long flow gets dport FS_DPORT (the FS class)."""
    cross = [(N + 3 + 2 * i, N + 4 + 2 * i) for i in range(N)]
    lines = [str(N + 1)]
    dport_long = FS_DPORT if fs_long else 100
    lines.append(f"{LONG_SRC} {LONG_DST} 3 {dport_long} 50000000 0.000000")
    for (cs, cd) in cross:
        lines.append(f"{cs} {cd} 3 100 50000000 0.000000")
    with open(os.path.join(HERE, "flows", f"{name}.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


def run(name, cc_mode, mix_dport=None, fs_long=False):
    gpl.build(N, flow_size=50_000_000, stop_time=0.2, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix=f"_{name}", cc_mode=cc_mode)
    cfgname = f"parking_lot_{N}bn_{name}"
    write_flows(cfgname, fs_long)
    cfg = os.path.join(HERE, "configs", f"hpcc_{cfgname}.yml")
    if mix_dport is not None:
        with open(cfg, "a") as f:
            f.write(f"mix_fs_dport: {mix_dport}\n")
    out = os.path.join(HERE, "output", cfgname)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{cfgname}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(f"{cfgname} exit {rc}")

    fcts, longf = {}, None
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) < 7:
                continue
            src, size, fct = ipid(p[0]), int(p[4]), int(p[6])
            if src == LONG_SRC:
                longf = fct
            else:
                fcts[src] = fct
    assert longf and len(fcts) == N, f"{cfgname}: {len(fcts)} cross flows"
    pfc = 0
    pfcf = os.path.join(out, "pfc.txt")
    if os.path.exists(pfcf):
        pfc = sum(1 for _ in open(pfcf))
    cross_mean = sum(fcts.values()) / len(fcts)
    return {"long": longf / 1e6, "cross_mean": cross_mean / 1e6,
            "ratio": longf / cross_mean, "pfc": pfc,
            "long_gbps": 50e6 * 8 / (longf / 1e9) / 1e9,
            "cross_gbps": 50e6 * 8 / (cross_mean / 1e9) / 1e9,
            "fct_path": os.path.join(out, "fct.txt")}


def main():
    print("=" * 78)
    print("REGRESSION GATES")
    print("=" * 78)
    stock = run("g1stock", 3)
    g1 = run("g1mix", 12, mix_dport=65535, fs_long=False)   # every flow stock class
    same = (open(stock["fct_path"]).read() == open(g1["fct_path"]).read())
    print(f"G1  cc_mode 3 vs cc_mode 12 (all-stock class): fct.txt identical = {same}")
    if not same:
        print(f"    stock long={stock['long']:.3f}ms  mixed long={g1['long']:.3f}ms")
    print(f"    stock: long/cross = {stock['ratio']:.3f}x, PFC={stock['pfc']}")

    purefs = run("g2fs", 11)
    g2 = run("g2mix", 12, mix_dport=1, fs_long=True)        # every flow FS class
    print(f"G2  cc_mode 11 long/cross = {purefs['ratio']:.3f}x  (PFC {purefs['pfc']})")
    print(f"    cc_mode 12 all-FS      = {g2['ratio']:.3f}x  (PFC {g2['pfc']})"
          f"   [FS pays stock's 42B INT here]")

    print()
    print("=" * 78)
    print("MIXED-MODE COEXISTENCE   (long flow = FS class, 4 cross flows = stock class)")
    print("=" * 78)
    mixed = run("coexist", 12, mix_dport=FS_DPORT, fs_long=True)

    hdr = f"{'configuration':<34} {'long':>9} {'cross':>9} {'ratio':>8} {'PFC':>5}"
    print(hdr)
    print("-" * len(hdr))
    for lab, r in (("all stock HPCC (cc_mode 3)", stock),
                   ("all HPCC-FS (cc_mode 11)", purefs),
                   ("MIXED: FS long + stock cross", mixed)):
        print(f"{lab:<34} {r['long']:>7.2f}ms {r['cross_mean']:>7.2f}ms "
              f"{r['ratio']:>7.3f}x {r['pfc']:>5}")

    print()
    print(f"  long-flow throughput : stock {stock['long_gbps']:.2f} Gbps  ->  "
          f"mixed {mixed['long_gbps']:.2f} Gbps   (fair share = {FAIR/1e9:.2f} Gbps)")
    print(f"  stock cross flows    : alone {stock['cross_gbps']:.2f} Gbps  ->  "
          f"beside FS {mixed['cross_gbps']:.2f} Gbps")
    print(f"  PFC in mixed run     : {mixed['pfc']}")


if __name__ == "__main__":
    main()
