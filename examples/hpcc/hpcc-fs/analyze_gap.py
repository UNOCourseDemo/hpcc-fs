#!/usr/bin/env python3
"""Quantify HPCC's multi-bottleneck gap vs a max-min-fair oracle.

Reads a parking-lot config (topology/flow/fct paths), computes the fluid max-min
optimal FCT for each flow (progressive filling, event-driven over flow arrivals and
completions, so staggered starts and asymmetric sizes are handled), and compares
against the simulated HPCC FCT.

Metrics:
  * per-flow slowdown   = actual_FCT / oracle_FCT  (uses --eff for achievable goodput)
  * RELATIVE PENALTY    = mean(long-path slowdown) / mean(short-path slowdown)
        Generalizes the equal-size "unfairness" ratio to asymmetric/staggered runs;
        oracle = 1.0. >1 means the multi-bottleneck (long) flow is penalized.
  * UNFAIRNESS          = long FCT / mean short FCT (only meaningful for equal sizes;
        printed when all flows are equal size and simultaneous).

NOTE: only valid while every flow's path has <= IntHeader::maxHop (5) switches; beyond
that, stock HPCC overflows INT and disables rate control (see findings.md F1).
"""
import argparse
import collections
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
HPCC_DIR = os.path.abspath(os.path.join(HERE, ".."))  # examples/hpcc
IP_BASE = 0x0B000001  # node id -> ip = IP_BASE + 256*id
INF = float("inf")


def node_from_ip_hex(h):
    return (int(h, 16) - IP_BASE) // 256


def parse_rate(s):
    m = re.match(r"([\d.]+)\s*([GMK]?)bps", s, re.I)
    if not m:
        raise ValueError(f"bad rate {s}")
    return float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6, "G": 1e9}[m.group(2).upper()]


def cfg_get(cfg_path, key):
    with open(cfg_path) as f:
        for line in f:
            if line.startswith(key + ":"):
                return line.split(":", 1)[1].strip()
    return None


def resolve(p):
    return p if os.path.isabs(p) else os.path.join(HPCC_DIR, p)


def parse_topology(path):
    with open(path) as f:
        toks = [l.split() for l in f if l.strip()]
    n_nodes, n_switch, n_links = (int(x) for x in toks[0])
    cap = {}
    adj = collections.defaultdict(list)
    for row in toks[2:2 + n_links]:
        a, b = int(row[0]), int(row[1])
        e = (min(a, b), max(a, b))
        cap[e] = parse_rate(row[2])
        adj[a].append(b)
        adj[b].append(a)
    return cap, adj


def shortest_path_links(src, dst, adj):
    prev = {src: None}
    q = collections.deque([src])
    while q:
        u = q.popleft()
        if u == dst:
            break
        for v in adj[u]:
            if v not in prev:
                prev[v] = u
                q.append(v)
    path, u = [], dst
    while u is not None:
        path.append(u)
        u = prev[u]
    path.reverse()
    return [(min(a, b), max(a, b)) for a, b in zip(path, path[1:])]


def parse_flows(path, adj):
    with open(path) as f:
        toks = [l.split() for l in f if l.strip()]
    flows = []
    for i, row in enumerate(toks[1:]):
        src, dst = int(row[0]), int(row[1])
        flows.append({"id": i, "src": src, "dst": dst,
                      "size_bits": int(row[4]) * 8, "start": float(row[5]),
                      "links": shortest_path_links(src, dst, adj)})
    return flows


def max_min_rates(active, flow_links, rem_cap):
    rates = {f: 0.0 for f in active}
    unfrozen = set(active)
    rem = dict(rem_cap)
    while unfrozen:
        share = None
        for link, c in rem.items():
            cnt = sum(1 for f in unfrozen if link in flow_links[f])
            if cnt and (share is None or c / cnt < share):
                share = c / cnt
        if share is None:
            break
        for f in unfrozen:
            rates[f] += share
        for link in rem:
            cnt = sum(1 for f in unfrozen if link in flow_links[f])
            rem[link] -= share * cnt
        frozen = {f for link in rem if rem[link] <= 1e-3
                  for f in unfrozen if link in flow_links[f]}
        if not frozen:
            break
        unfrozen -= frozen
    return rates


def oracle_fct(flows, cap, eff):
    """Event-driven fluid max-min FCT (ns) per flow id; honors per-flow start times."""
    rem_cap = {e: c * eff for e, c in cap.items()}
    flow_links = {f["id"]: f["links"] for f in flows}
    remaining = {f["id"]: f["size_bits"] for f in flows}
    start = {f["id"]: f["start"] for f in flows}
    not_started = set(remaining)
    active, fct, t = set(), {}, 0.0
    while not_started or active:
        for fid in list(not_started):
            if start[fid] <= t + 1e-15:
                active.add(fid)
                not_started.discard(fid)
        if not active:
            t = min(start[fid] for fid in not_started)
            continue
        rates = max_min_rates(active, flow_links, rem_cap)
        comp_dt = min((remaining[f] / rates[f] for f in active if rates[f] > 0), default=INF)
        arr_dt = min((start[fid] - t for fid in not_started), default=INF)
        dt = min(comp_dt, arr_dt)
        for f in active:
            remaining[f] -= rates[f] * dt
        t += dt
        for f in list(active):
            if remaining[f] <= 1.0:
                fct[f] = (t - start[f]) * 1e9
                active.discard(f)
    return fct


def parse_actual_fct(path):
    out = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                c = line.split()
                if len(c) >= 7:
                    out[(node_from_ip_hex(c[0]), node_from_ip_hex(c[1]))] = int(c[6])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--eff", type=float, default=0.95)
    args = ap.parse_args()

    cfg = resolve(args.config)
    if not os.path.exists(cfg):
        cfg = os.path.join(HERE, "configs", os.path.basename(args.config))
    cap, adj = parse_topology(resolve(cfg_get(cfg, "topology_file")))
    flows = parse_flows(resolve(cfg_get(cfg, "flow_file")), adj)
    bn = min(cap.values())
    for fl in flows:
        fl["nbn"] = sum(1 for e in fl["links"] if cap[e] == bn)
    o_fct = oracle_fct(flows, cap, args.eff)
    a_fct = parse_actual_fct(resolve(cfg_get(cfg, "fct_output_file")))

    max_nbn = max(fl["nbn"] for fl in flows)
    equal_simul = (len({fl["size_bits"] for fl in flows}) == 1
                   and len({fl["start"] for fl in flows}) == 1)
    print(f"\n== {os.path.basename(cfg)} ==")
    print(f"{'flow':>5} {'src->dst':>9} {'bn':>3} {'size_MB':>8} {'start_ms':>9} "
          f"{'actual_ms':>10} {'oracle_ms':>10} {'slowdown':>9}")
    long_sd, short_sd, long_fct, short_fct = [], [], [], []
    for fl in sorted(flows, key=lambda x: (-x["nbn"], x["id"])):
        a = a_fct.get((fl["src"], fl["dst"]))
        o = o_fct[fl["id"]]
        sd = (a / o) if a else float("nan")
        label = f"{fl['src']}->{fl['dst']}"
        print(f"{fl['id']:>5} {label:>9} {fl['nbn']:>3} {fl['size_bits']/8e6:>8.1f} "
              f"{fl['start']*1e3:>9.2f} {(a/1e6 if a else float('nan')):>10.3f} "
              f"{o/1e6:>10.3f} {sd:>9.3f}")
        if a:
            if fl["nbn"] == max_nbn:
                long_sd.append(sd); long_fct.append(a)
            else:
                short_sd.append(sd); short_fct.append(a)

    if long_sd and short_sd:
        lsd = sum(long_sd) / len(long_sd)
        ssd = sum(short_sd) / len(short_sd)
        penalty = lsd / ssd
        print(f"\n  bottlenecks(N)              = {max_nbn}")
        print(f"  long-path mean slowdown     = {lsd:.3f}x oracle")
        print(f"  short-path mean slowdown    = {ssd:.3f}x oracle")
        print(f"  RELATIVE PENALTY long/short = {penalty:.3f}x   (oracle = 1.000x)")
        if equal_simul:
            unfair = (max(long_fct) / (sum(short_fct) / len(short_fct)))
            print(f"  UNFAIRNESS (long/short FCT) = {unfair:.3f}x")
            print(f"CSV,{max_nbn},{max(long_fct)/1e6:.4f},"
                  f"{(sum(short_fct)/len(short_fct))/1e6:.4f},{unfair:.4f}")
        else:
            print(f"CSV,{max_nbn},{(sum(long_fct)/len(long_fct))/1e6:.4f},"
                  f"{(sum(short_fct)/len(short_fct))/1e6:.4f},{penalty:.4f}")
    else:
        print("  (incomplete FCT data; flows may not have finished)")


if __name__ == "__main__":
    main()
