#!/usr/bin/env python3
"""Heterogeneous / dynamic contention matrix (round-2 review, MC3).

Extends the parking lot beyond its uniform, one-competitor-per-link form:

  S1 hetero-cap   per-link capacities [25,10,25,40] Gbps (long flow's fair
                  share set by the 10 G link)
  S2 unequal      uniform 25 G, but [3,1,2,1] cross flows per link
  S3 two longs    two multi-bottleneck flows with overlapping spans
                  (A spans links 1-4, B spans links 2-3) + 1 cross per link
  S4 churn        cross flows arrive staggered (10 ms apart, 25 MB) and
                  depart on completion; long flow 100 MB from t=0
  S5 hetero-RTT   RDMA-RCP itself under 4x bottleneck-delay spread and
                  8x cross-host-delay spread (the diagnosis sweeps applied
                  to the mode, not just to HPCC)

Because equal-share intuition breaks in S1-S4, every scenario is scored
against a generic event-driven progressive-filling max-min oracle computed
on the actual topology and arrival schedule. Metric: per-flow penalty =
sim FCT / oracle FCT; we report the long flow's penalty (S3: worst long).

Run from the repo root:
    venv/bin/python examples/hpcc/hpcc-fs/run_stress_matrix.py
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

MB = 8e6  # bits per MB(decimal) -> we use bytes*8 below instead


# ---------------------------------------------------------------- oracle ----
def maxmin_rates(active, caps):
    """Progressive filling. active: {fid: set(link_ids)}; caps: {lid: bps}.
    Returns {fid: rate}."""
    rates = {}
    rem = dict(caps)
    unfrozen = dict(active)
    while unfrozen:
        # per-link equal share among unfrozen flows crossing it
        best = None
        for lid, c in rem.items():
            n = sum(1 for L in unfrozen.values() if lid in L)
            if n == 0:
                continue
            share = c / n
            if best is None or share < best[0]:
                best = (share, lid)
        if best is None:
            for f in unfrozen:
                rates[f] = float("inf")
            break
        share, lid = best
        frozen = [f for f, L in unfrozen.items() if lid in L]
        for f in frozen:
            rates[f] = share
            for l2 in unfrozen[f]:
                rem[l2] -= share
            del unfrozen[f]
        rem = {l: max(c, 0.0) for l, c in rem.items()}
    return rates


def oracle_fcts(flows, caps):
    """flows: {fid: (links:set, size_bits, start_s)}. Event-driven max-min.
    Returns {fid: fct_seconds}."""
    remaining = {f: s for f, (_, s, _) in flows.items()}
    start = {f: st for f, (_, _, st) in flows.items()}
    links = {f: L for f, (L, _, _) in flows.items()}
    t = 0.0
    done = {}
    pending = sorted(flows, key=lambda f: start[f])
    active = {}
    while pending or active:
        rates = maxmin_rates({f: links[f] for f in active}, caps) if active else {}
        # next event: arrival or completion
        t_arr = start[pending[0]] if pending else float("inf")
        t_fin, fin_f = float("inf"), None
        for f in active:
            r = rates[f]
            tf = t + (remaining[f] / r if r > 0 else float("inf"))
            if tf < t_fin:
                t_fin, fin_f = tf, f
        t_next = min(t_arr, t_fin)
        for f in active:
            remaining[f] -= rates[f] * (t_next - t)
        t = t_next
        if t_fin <= t_arr and fin_f is not None:
            done[fin_f] = t - start[fin_f]
            active.pop(fin_f)
        else:
            f = pending.pop(0)
            active[f] = True
    return done


# ------------------------------------------------------------- topology ----
def build_scenario(name, caps_gbps, crosses_per_link, longs, flows_extra=None,
                   cc_mode=3, stop=0.4):
    """caps_gbps[i] = capacity of link i (switch i -- switch i+1).
    crosses_per_link[i] = #cross flows on link i.
    longs = [(first_link, last_link, size_bytes, start_s)].
    Returns (flow_defs {fid:(links,size_bits,start)}, sim host map)."""
    N = len(caps_gbps)
    n_switch = N + 1
    links = []          # (a, b, rate, delay)
    for i in range(N):
        links.append((i, i + 1, f"{caps_gbps[i]}Gbps", "0.002ms"))
    host = n_switch     # next node id
    flow_lines = []
    flow_defs = {}
    sim_src = {}        # fid -> src host id
    fid = 0
    # long flows: src attached to switch first, dst to switch last+1
    for (a, b, size, st) in longs:
        s_h, d_h = host, host + 1
        host += 2
        links.append((a, s_h, "100Gbps", "0.001ms"))
        links.append((b + 1, d_h, "100Gbps", "0.001ms"))
        flow_lines.append((s_h, d_h, size, st))
        flow_defs[fid] = (set(range(a, b + 1)), size * 8, st)
        sim_src[fid] = s_h
        fid += 1
    # cross flows
    for i in range(N):
        for _ in range(crosses_per_link[i]):
            s_h, d_h = host, host + 1
            host += 2
            links.append((i, s_h, "100Gbps", "0.001ms"))
            links.append((i + 1, d_h, "100Gbps", "0.001ms"))
            flow_lines.append((s_h, d_h, 50_000_000, 0.0))
            flow_defs[fid] = ({i}, 50_000_000 * 8, 0.0)
            sim_src[fid] = s_h
            fid += 1
    if flows_extra:
        for (link_i, size, st) in flows_extra:
            s_h, d_h = host, host + 1
            host += 2
            links.append((link_i, s_h, "100Gbps", "0.001ms"))
            links.append((link_i + 1, d_h, "100Gbps", "0.001ms"))
            flow_lines.append((s_h, d_h, size, st))
            flow_defs[fid] = ({link_i}, size * 8, st)
            sim_src[fid] = s_h
            fid += 1
    n_nodes = host
    # write via the standard generator for the config skeleton, then overwrite
    gpl.build(N, flow_size=50_000_000, stop_time=stop, bn_delay="0.002ms",
              has_win=1, var_win="true", suffix=f"_{name}", cc_mode=cc_mode)
    base = f"parking_lot_{N}bn_{name}"
    topo = [f"{n_nodes} {n_switch} {len(links)}",
            " ".join(str(i) for i in range(n_switch))]
    topo += [f"{a} {b} {r} {d} 0" for (a, b, r, d) in links]
    with open(os.path.join(HERE, "topologies", f"{base}.txt"), "w") as f:
        f.write("\n".join(topo) + "\n")
    fl = sorted(flow_lines, key=lambda x: x[3])
    out = [str(len(fl))] + [f"{s} {d} 3 100 {sz} {st:.6f}" for (s, d, sz, st) in fl]
    with open(os.path.join(HERE, "flows", f"{base}.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(HERE, "traces", f"{base}_nodes.txt"), "w") as f:
        f.write(f"{n_nodes}\n" + " ".join(str(i) for i in range(n_nodes)) + "\n")
    # ECN maps must cover every link rate in the topology. yaml-cpp keeps the
    # FIRST duplicate key, so replace the template's maps in place rather than
    # appending. Note: HPCC's INT wire format only encodes the discrete rates
    # {25,50,100,200,400} Gbps, so scenarios must use those.
    cfgp = os.path.join(HERE, "configs", f"hpcc_{base}.yml")
    cfg = open(cfgp).read()
    cfg = cfg.replace("kmax_map:\n  25000000000: 400\n  100000000000: 1600",
                      "kmax_map:\n  25000000000: 400\n  50000000000: 800\n  100000000000: 1600")
    cfg = cfg.replace("kmin_map:\n  25000000000: 100\n  100000000000: 400",
                      "kmin_map:\n  25000000000: 100\n  50000000000: 200\n  100000000000: 400")
    cfg = cfg.replace("pmax_map:\n  25000000000: 0.2\n  100000000000: 0.2",
                      "pmax_map:\n  25000000000: 0.2\n  50000000000: 0.2\n  100000000000: 0.2")
    open(cfgp, "w").write(cfg)
    caps = {i: caps_gbps[i] * 1e9 for i in range(N)}
    return base, flow_defs, sim_src, caps


def ipid(h):
    return (int(h, 16) >> 8) & 0xFFFF


def run(base):
    out = os.path.join(HERE, "output", base)
    os.makedirs(out, exist_ok=True)
    for fn in os.listdir(out):
        os.remove(os.path.join(out, fn))
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{base}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(base)
    fct = {}
    with open(os.path.join(out, "fct.txt")) as f:
        for ln in f:
            p = ln.split()
            if len(p) >= 7:
                fct[ipid(p[0])] = int(p[6]) / 1e9  # seconds
    return fct


def penalty(base, flow_defs, sim_src, caps, long_fids):
    """Returns (generalized unfairness, worst-long oracle-normalized penalty).
    Generalized unfairness = worst-long penalty / best-flow penalty, where
    penalty_f = simFCT_f / oracleFCT_f. In the uniform equal-size case this
    reduces exactly to the paper's headline ratio (long FCT / mean cross FCT),
    since all oracle FCTs coincide; under heterogeneity it compares each flow
    against its OWN max-min entitlement."""
    fct = run(base)
    ofct = oracle_fcts(flow_defs, caps)
    pens = {f: fct[sim_src[f]] / ofct[f] for f in flow_defs if sim_src[f] in fct}
    wl = max(pens[f] for f in long_fids)
    return wl / min(pens.values()), wl


def scen(name, caps_gbps, crosses, longs, extra=None):
    rows = {}
    for cc, lab in ((3, "s"), (11, "f")):
        base, fd, ss, caps = build_scenario(f"{name}{lab}", caps_gbps, crosses,
                                            longs, extra, cc_mode=cc)
        nlong = len(longs)
        lp, wp = penalty(base, fd, ss, caps, list(range(nlong)))
        rows[cc] = (lp, wp)
    return rows


def main():
    print(f"{'scenario':<22} | {'stock unf':>10} {'o-pen':>7} | {'RCP unf':>9} {'o-pen':>7}")
    print("-" * 66)
    S = 50_000_000
    tests = [
        ("S1 hetero-cap", [25, 50, 25, 100], [1, 1, 1, 1], [(0, 3, S, 0.0)], None),
        ("S2 unequal-comp", [25, 25, 25, 25], [3, 1, 2, 1], [(0, 3, S, 0.0)], None),
        ("S3 two-longs", [25, 25, 25, 25], [1, 1, 1, 1],
         [(0, 3, S, 0.0), (1, 2, S, 0.0)], None),
        ("S4 churn", [25, 25, 25, 25], [0, 0, 0, 0], [(0, 3, 100_000_000, 0.0)],
         [(0, 25_000_000, 0.000), (1, 25_000_000, 0.010),
          (2, 25_000_000, 0.020), (3, 25_000_000, 0.030),
          (0, 25_000_000, 0.040), (2, 25_000_000, 0.050)]),
    ]
    for name, caps, crosses, longs, extra in tests:
        r = scen(name.split()[0], caps, crosses, longs, extra)
        print(f"{name:<22} | {r[3][0]:>9.3f}x {r[3][1]:>6.2f}x | "
              f"{r[11][0]:>8.3f}x {r[11][1]:>6.2f}x")   # (unfairness, long oracle-norm)

    # S5: RDMA-RCP under heterogeneous RTT (existing generator knobs)
    print()
    print("S5 hetero-RTT under RDMA-RCP (long-flow unfairness ratio, uniform links):")
    for bnd, chd in (("0.002ms", "0.001ms"), ("0.008ms", "0.001ms"),
                     ("0.002ms", "0.008ms"), ("0.008ms", "0.008ms")):
        tag = f"rtt{bnd.replace('.','').replace('ms','')}_{chd.replace('.','').replace('ms','')}"
        gpl.build(4, flow_size=S, stop_time=0.25, bn_delay=bnd,
                  has_win=1, var_win="true", suffix=f"_{tag}", cc_mode=11,
                  cross_host_delay=chd)
        fct = run(f"parking_lot_4bn_{tag}")
        lo = fct[5]
        cr = [v for k, v in fct.items() if k != 5]
        print(f"  bn_delay={bnd} cross_host_delay={chd}: {lo/(sum(cr)/len(cr)):.3f}x")


if __name__ == "__main__":
    main()
