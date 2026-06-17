#!/usr/bin/env python3
"""Jain's Fairness Index on FCT slowdowns for mixed-size workloads.

Jain's FI:  JFI(x_1..x_n) = (sum x_i)^2 / (n * sum x_i^2),  range [1/n, 1].
Higher is fairer. We apply it to per-flow FCT slowdowns (actual / standalone), grouped by:
  - all flows together
  - by path-class (long-path / short-path)
  - by size bucket

Usage:
    venv/bin/python jain_analysis.py <stock_config.yml> <fs_config.yml>
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_gap as ag

IP_BASE = 0x0B000001


def jain(values):
    if not values:
        return None
    n = len(values)
    s = sum(values)
    s2 = sum(v * v for v in values)
    if s2 == 0:
        return 1.0
    return (s * s) / (n * s2)


def size_bucket(size_bytes):
    if size_bytes < 10_000:
        return "small (<10 KB)"
    if size_bytes < 100_000:
        return "medium (10-100 KB)"
    if size_bytes < 1_000_000:
        return "large (100 KB-1 MB)"
    return "elephant (>1 MB)"


def analyze(config_path):
    cfg = ag.resolve(config_path)
    if not os.path.exists(cfg):
        cfg = os.path.join(ag.HERE, "configs", os.path.basename(config_path))
    cap, adj = ag.parse_topology(ag.resolve(ag.cfg_get(cfg, "topology_file")))
    flows = ag.parse_flows(ag.resolve(ag.cfg_get(cfg, "flow_file")), adj)
    bn = min(cap.values())
    for fl in flows:
        fl["nbn"] = sum(1 for e in fl["links"] if cap[e] == bn)
    max_nbn = max(fl["nbn"] for fl in flows)

    o_fct = ag.oracle_fct(flows, cap, eff=0.95)
    a_fct = ag.parse_actual_fct(ag.resolve(ag.cfg_get(cfg, "fct_output_file")))

    by_class = collections.defaultdict(list)   # "long" / "short"
    by_bucket = collections.defaultdict(list)  # size buckets
    all_slow = []
    for fl in flows:
        a = a_fct.get((fl["src"], fl["dst"]))
        if a is None:
            continue
        slow = a / o_fct[fl["id"]]
        klass = "long" if fl["nbn"] == max_nbn else "short"
        bkt = size_bucket(fl["size_bits"] // 8)
        by_class[klass].append(slow)
        by_bucket[bkt].append(slow)
        all_slow.append(slow)
    return all_slow, by_class, by_bucket


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stock", help="stock cc_mode 3 config")
    ap.add_argument("fs", help="HPCC-FS cc_mode 11 config")
    args = ap.parse_args()

    print(f"\n{'=' * 76}")
    print(f"  Jain's Fairness Index on FCT slowdowns (higher = fairer; max 1.0)")
    print(f"{'=' * 76}\n")

    s_all, s_class, s_buck = analyze(args.stock)
    f_all, f_class, f_buck = analyze(args.fs)

    print(f"  {'group':>22} {'n':>6}   {'JFI stock':>10} {'JFI FS':>10}   "
          f"{'mean slowdown stock':>22} {'mean slowdown FS':>22}")

    def line(label, sv, fv):
        if not sv or not fv:
            print(f"  {label:>22} {'n/a':>6}")
            return
        js = jain(sv); jf = jain(fv)
        ms = sum(sv) / len(sv); mf = sum(fv) / len(fv)
        print(f"  {label:>22} {len(sv):>6}   {js:>10.4f} {jf:>10.4f}   "
              f"{ms:>22.2f} {mf:>22.2f}")

    line("ALL flows", s_all, f_all)
    print()
    for k in ("long", "short"):
        line(f"by class: {k}", s_class.get(k, []), f_class.get(k, []))
    print()
    for bkt in ("small (<10 KB)", "medium (10-100 KB)", "large (100 KB-1 MB)", "elephant (>1 MB)"):
        line(f"size: {bkt}", s_buck.get(bkt, []), f_buck.get(bkt, []))


if __name__ == "__main__":
    main()
