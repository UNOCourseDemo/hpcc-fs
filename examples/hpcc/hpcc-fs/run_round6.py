#!/usr/bin/env python3
"""Enhancement round 6a: high fan-in — verify the oscillation, then damp it.

T  Rate time-series at S=64 (reviewer Q1's trace): receiver-side goodput,
   binned, aggregate + per-flow spread. Verifies (or refutes) section 5.11's
   "oscillates between overshoot and the floor rail" — currently inferred
   from lifetime utilization only.
S  Stabilization sweep with EXISTING knobs: fs_d_scale (longer averaging /
   update interval) x fs_alpha (smaller gain) at S=64; best configs re-tested
   at 10 MB (persistence) and S=128, plus an N=4 fairness regression gate.

Run from repo root: venv/bin/python examples/hpcc/hpcc-fs/run_round6.py
"""
import collections
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")
sys.path.insert(0, HERE)
import gen_parking_lot as gpl  # noqa: E402

C_BPS = 25e9
REC = 56
IP_BASE = 0x0B000001


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


def fcts_of(out):
    fcts = []
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) >= 7:
                fcts.append(int(p[6]))
    return fcts


def pfc_count(out):
    f = os.path.join(out, "pfc.txt")
    return sum(1 for ln in open(f) if ln.split()[5] == "1") if os.path.exists(f) else 0


def build_incast(S, size, tag, cc=11, floor="100Mb/s", d_scale=None, alpha=0.4,
                 trace=False):
    n_nodes = S + 2
    stop = max(0.1, S * size * 8 / C_BPS * 6)
    gpl.build(1, flow_size=size, stop_time=stop, bn_delay="0.001ms",
              has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=cc,
              fs_alpha=alpha, enable_trace=1 if trace else 0, trace_rx=trace)
    base = f"parking_lot_1bn_{tag}"
    topo = [f"{n_nodes} 1 {S+1}", "0", "0 1 25Gbps 0.001ms 0"]
    topo += [f"0 {i} 100Gbps 0.001ms 0" for i in range(2, S + 2)]
    with open(os.path.join(HERE, "topologies", f"{base}.txt"), "w") as fh:
        fh.write("\n".join(topo) + "\n")
    flows = [str(S)] + [f"{i} 1 3 100 {size} 0.000000" for i in range(2, S + 2)]
    with open(os.path.join(HERE, "flows", f"{base}.txt"), "w") as fh:
        fh.write("\n".join(flows) + "\n")
    # trace only the receiver (node 1): RX records give goodput
    with open(os.path.join(HERE, "traces", f"{base}_nodes.txt"), "w") as fh:
        fh.write("1\n1\n" if trace else
                 f"{n_nodes}\n" + " ".join(str(i) for i in range(n_nodes)) + "\n")
    cfgp = os.path.join(HERE, "configs", f"hpcc_{base}.yml")
    with open(cfgp, "a") as fh:
        fh.write(f"fs_min_rate: {floor}\n")
        if d_scale:
            fh.write(f"fs_d_scale: {d_scale}\n")
    return base


def parse_rx_trace(tr_path, bin_ms=0.2):
    with open(tr_path, "rb") as f:
        data = f.read()
    (ln,) = struct.unpack_from("<I", data, 0)
    hdr = 4 + ln * 11 + 4
    binw = bin_ms * 1e6
    per_flow = collections.defaultdict(lambda: collections.defaultdict(int))
    off = hdr
    while off + REC <= len(data):
        if data[off + 27] == 0 and data[off + 29] == 0 and data[off + 26] == 0x11:
            t = struct.unpack_from("<Q", data, off)[0]
            sip = struct.unpack_from("<I", data, off + 16)[0]
            size = struct.unpack_from("<H", data, off + 24)[0]
            per_flow[(sip - IP_BASE) // 256][int(t // binw)] += size
        off += REC
    return per_flow, bin_ms


def part_t():
    print("== T. rate time-series at S=64 (10 MB flows, floor 100M, RX trace) ==")
    base = build_incast(64, 10_000_000, "r6trace", trace=True)
    out = run_sim(base)
    per_flow, bin_ms = parse_rx_trace(os.path.join(out, "trace.tr"))
    n_bins = max(b for d in per_flow.values() for b in d) + 1
    agg = [0.0] * n_bins
    for d in per_flow.values():
        for b, byt in d.items():
            agg[b] += byt * 8 / (bin_ms * 1e6)  # Gbps
    print(f"  aggregate goodput, {bin_ms} ms bins (C = 25 Gbps):")
    for i in range(0, min(n_bins, 300), 15):
        seg = agg[i:i + 15]
        bars = "".join("#" if v > 20 else "+" if v > 12.5 else "-" if v > 5
                       else "." for v in seg)
        print(f"   t={i*bin_ms:6.1f}ms  [{bars}]  mean {sum(seg)/len(seg):5.1f} Gbps")
    active = [v for v in agg if v > 0.1]
    print(f"  aggregate over active period: min {min(active):.1f}  "
          f"mean {sum(active)/len(active):.1f}  max {max(active):.1f} Gbps")
    lo = sum(1 for v in active if v < 12.5) / len(active)
    print(f"  fraction of active bins below C/2: {lo:.2f}")


def sweep_case(S, size, d_scale, alpha, tag):
    base = build_incast(S, size, tag, d_scale=d_scale, alpha=alpha)
    out = run_sim(base)
    fcts = fcts_of(out)
    assert len(fcts) == S, (tag, len(fcts))
    mean = sum(fcts) / len(fcts)
    bound = S * size * 8 / C_BPS * 1e9
    return bound / mean, pfc_count(out)


def part_s():
    print("== S. stabilization sweep at S=64, 200 KB (baseline util 0.47) ==")
    print(f"  {'d_scale':>8} {'alpha':>6} {'util':>6} {'PFC':>5}")
    results = {}
    grid = [(None, 0.4), (2, 0.4), (4, 0.4), (8, 0.4),
            (None, 0.2), (None, 0.1), (2, 0.2), (4, 0.2), (4, 0.1)]
    for d, a in grid:
        tag = f"r6s_d{d or 1}_a{str(a).replace('.','p')}"
        util, pfc = sweep_case(64, 200_000, d, a, tag)
        results[(d, a)] = util
        print(f"  {d or 1:>8} {a:>6} {util:>6.2f} {pfc:>5}")
    best = sorted(results, key=results.get, reverse=True)[:2]
    print("  -- persistence + scale checks on the two best configs --")
    print(f"  {'config':>14} {'case':>14} {'util':>6} {'PFC':>5}")
    for d, a in best:
        for S, size, lab in ((64, 10_000_000, "S=64 10MB"), (128, 200_000, "S=128 200KB")):
            tag = f"r6v_d{d or 1}_a{str(a).replace('.','p')}_{S}_{size//1000}"
            util, pfc = sweep_case(S, size, d, a, tag)
            print(f"  d{d or 1}/a{a:>4} {lab:>14} {util:>6.2f} {pfc:>5}")
    print("  -- N=4 fairness gate under the best config --")
    d, a = best[0]
    gpl.build(4, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix="_r6gate", cc_mode=11, fs_alpha=a)
    if d:
        with open(os.path.join(HERE, "configs", "hpcc_parking_lot_4bn_r6gate.yml"), "a") as fh:
            fh.write(f"fs_d_scale: {d}\n")
    out = run_sim("parking_lot_4bn_r6gate")
    per = {}
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) >= 7:
                per.setdefault(ipid(p[0]), []).append(int(p[6]))
    lo = per[5][0]
    cr = [v[0] for k, v in per.items() if k != 5]
    print(f"  d{d or 1}/a{a}: N=4 unfairness {lo/(sum(cr)/len(cr)):.3f}x  "
          f"PFC {pfc_count(out)}")


def part_f():
    print("== F. Q16 fixed-point switch update vs floating point (references in parens) ==")
    import run_allreduce_jct as J
    import gen_fattree_k4 as g4
    # N-sweep, double refs: 1.003 / 1.003 / 1.005
    for n, ref in ((2, 1.003), (3, 1.003), (4, 1.005)):
        tag = f"r6f_n{n}"
        gpl.build(n, flow_size=50_000_000, stop_time=0.25, bn_delay="0.002ms",
                  has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=11)
        with open(os.path.join(HERE, "configs", f"hpcc_parking_lot_{n}bn_{tag}.yml"), "a") as fh:
            fh.write("fs_fixed_point: 16\n")
        out = run_sim(f"parking_lot_{n}bn_{tag}")
        per = {}
        with open(os.path.join(out, "fct.txt")) as f:
            for ln in f:
                p2 = ln.split()
                if len(p2) >= 7:
                    per.setdefault(ipid(p2[0]), []).append(int(p2[6]))
        long_id = max(per)  # long src has the highest host id in gpl layout? use known: long=n+... 
        # long flow src is host id 2*n+... use the flow with max FCT instead (long is slowest pre-fix,
        # equal post-fix; identify long as the id present in every build: id (2n+1)? robust: unfairness
        # via slowest/mean-of-rest is equivalent at ~1.0
        fcts = sorted(v[0] for v in per.values())
        unf = fcts[-1] / (sum(fcts[:-1]) / (len(fcts) - 1))
        print(f"  N={n} parking lot: unfairness {unf:.3f}x (double: {ref:.3f}x)  PFC {pfc_count(out)}")
    # ring JCT, double ref 17.99 ms
    name = "ft4_r6f_jct"
    g4.build(name, cc_mode=11)
    J.write_flows(name, False)
    with open(os.path.join(HERE, "configs", f"hpcc_{name}.yml"), "a") as fh:
        fh.write("fs_fixed_point: 16\n")
    out = run_sim(name)
    ring = {(a, b) for (a, b) in J.RING}
    fs = []
    with open(os.path.join(out, "fct.txt")) as fh:
        for ln in fh:
            p2 = ln.split()
            if len(p2) >= 7 and (ipid(p2[0]), ipid(p2[1])) in ring:
                fs.append(int(p2[6]))
    print(f"  ring coflow JCT: {max(fs)/1e6:.2f} ms (double: 17.99 ms)")
    # incast S=64, d_scale 2, double ref util 0.84
    base = build_incast(64, 200_000, "r6f_in64", d_scale=2)
    with open(os.path.join(HERE, "configs", "hpcc_parking_lot_1bn_r6f_in64.yml"), "a") as fh:
        fh.write("fs_fixed_point: 16\n")
    out = run_sim(base)
    fcts = fcts_of(out)
    util = (64 * 200_000 * 8 / C_BPS * 1e9) / (sum(fcts) / len(fcts))
    print(f"  incast S=64 (d x2): utilization {util:.2f} (double: 0.84)  PFC {pfc_count(out)}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("parts", nargs="?", default="tsf")
    parts = ap.parse_args().parts
    if "t" in parts: part_t(); print()
    if "s" in parts: part_s(); print()
    if "f" in parts: part_f()
