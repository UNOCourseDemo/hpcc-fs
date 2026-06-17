#!/usr/bin/env python3
"""Analyze the repro-verification campaign and compare to the original HPCC paper trends.

Reads results/raw/<config>/{fct.txt,pfc.txt,bottleneck.txt} (collected from the VMs) and emits,
per (workload, load) cell, a table of FCT-slowdown statistics per scheme plus PFC and peak queue.

FCT slowdown = fct / standalone_fct  (fct.txt cols, 0-indexed: 4=size 6=fct 7=standalone_fct).
The paper's headline metric is the *short-flow tail* (p99 slowdown for <3 KB in WebSearch, <120 KB
in FB_Hadoop): HPCC should be far below DCQCN/TIMELY, with near-zero queue and ~no PFC.

Usage:  python3 analyze_repro.py [results/raw]
"""
import os, sys, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "raw")

SCHEMES = ["hpcc", "dcqcn", "timely", "dctcp", "hpcc_pint"]
WORKLOADS = ["ws", "fb"]
LOADS = ["30", "50", "70"]
# short-flow threshold per workload (bytes), per the paper
SHORT = {"ws": 3_000, "fb": 120_000}


def load_fct(path):
    """Return (sizes, slowdowns) arrays for a config's fct.txt, or (None, None)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None, None
    sizes, slow = [], []
    with open(path) as f:
        for ln in f:
            p = ln.split()
            if len(p) < 8:
                continue
            try:
                size = int(p[4]); fct = int(p[6]); std = int(p[7])
            except ValueError:
                continue
            if std <= 0:
                continue
            sizes.append(size); slow.append(fct / std)
    if not sizes:
        return None, None
    return np.array(sizes), np.array(slow)


def pfc_count(d):
    f = os.path.join(d, "pfc.txt")
    if not os.path.exists(f):
        return None
    return sum(1 for ln in open(f) if ln.strip())


def peak_queue_kb(d):
    """Peak per-port egress queue (KB). bottleneck.txt columns:
    sw port pg max_egress_bytes kmin kmax ...  (max_overall line prefixes an extra token).
    """
    f = os.path.join(d, "bottleneck.txt")
    if not os.path.exists(f):
        return None
    best = 0
    for ln in open(f):
        p = ln.split()
        if not p:
            continue
        if p[0] == "max_overall" and len(p) > 4:        # summary line: field 4 = max_egress_bytes
            try: best = max(best, int(p[4]))
            except ValueError: pass
        elif len(p) >= 4 and p[0].isdigit():            # per-port line: field 3 = max_egress_bytes
            try: best = max(best, int(p[3]))
            except ValueError: pass
    return round(best / 1000) if best else 0


def stats(slow):
    return (np.mean(slow), np.percentile(slow, 50),
            np.percentile(slow, 95), np.percentile(slow, 99))


def main():
    print(f"# Repro-verification analysis  (raw = {RAW})\n")
    summary = {}
    for wl in WORKLOADS:
        for load in LOADS:
            rows = []
            for sc in SCHEMES:
                name = f"{sc}_{wl}_{load}"
                d = os.path.join(RAW, name)
                sizes, slow = load_fct(os.path.join(d, "fct.txt"))
                if slow is None:
                    rows.append((sc, None)); continue
                short_mask = sizes <= SHORT[wl]
                overall = stats(slow)
                short = stats(slow[short_mask]) if short_mask.any() else (None,)*4
                rows.append((sc, dict(n=len(slow), n_short=int(short_mask.sum()),
                                      overall=overall, short=short,
                                      pfc=pfc_count(d), pq=peak_queue_kb(d))))
            summary[(wl, load)] = rows
            print(f"\n## {wl.upper()}  {load}% load   (short flow = <{SHORT[wl]//1000}KB)")
            print(f"{'scheme':>10} {'flows':>8} {'short_n':>8} | "
                  f"{'p99_all':>8} {'p99_short':>10} {'p50_short':>10} {'mean_all':>9} | "
                  f"{'PFC':>6} {'peakQ_KB':>9}")
            for sc, r in rows:
                if r is None:
                    print(f"{sc:>10} {'--- no data (run missing/failed) ---':>60}"); continue
                oa = r['overall']; sh = r['short']
                p99a = f"{oa[3]:.2f}"; p99s = f"{sh[3]:.2f}" if sh[3] else "-"
                p50s = f"{sh[1]:.2f}" if sh[1] else "-"; mna = f"{oa[0]:.2f}"
                print(f"{sc:>10} {r['n']:>8} {r['n_short']:>8} | "
                      f"{p99a:>8} {p99s:>10} {p50s:>10} {mna:>9} | "
                      f"{str(r['pfc']):>6} {str(r['pq']):>9}")
    # paper-trend checks
    print("\n\n# Paper-trend checks (qualitative)")
    for (wl, load), rows in summary.items():
        m = {sc: r for sc, r in rows if r}
        if "hpcc" in m and "dcqcn" in m:
            h = m["hpcc"]["short"][3]; d = m["dcqcn"]["short"][3]
            if h and d:
                verdict = "PASS" if h < d else "CHECK"
                print(f"  {wl} {load}%: HPCC short-flow p99={h:.2f} vs DCQCN={d:.2f}  "
                      f"-> HPCC {'<' if h<d else '>='} DCQCN  [{verdict}]")


if __name__ == "__main__":
    main()
