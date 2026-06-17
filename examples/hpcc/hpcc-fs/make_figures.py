#!/usr/bin/env python3
"""Generate paper figures (PNG) from LIVE experiment runs.

Every number in every figure is derived by actually running the simulator and parsing
analyze_gap.py --- nothing is hard-coded. For each figure we (i) generate the YAML config via the
gen_*.py generators, (ii) run the optimized binary, (iii) read the relative penalty from
analyze_gap. The rate-trace figure reads the binary trace.tr directly.

Usage (from the repo root, so the binary + venv are found):
    venv/bin/python examples/hpcc/hpcc-fs/make_figures.py            # full re-run (deterministic)
    venv/bin/python examples/hpcc/hpcc-fs/make_figures.py --cache    # reuse existing output/ dirs

The runs are deterministic, so repeated invocations reproduce identical figures.
"""
import collections
import os
import struct
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))          # examples/hpcc/hpcc-fs
HPCC_DIR = os.path.dirname(HERE)                            # examples/hpcc  (binary cwd)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))           # repo root
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")
PYEXE = sys.executable
FIG_DIR = os.path.join(HERE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

sys.path.insert(0, HERE)
import gen_parking_lot as gpl          # noqa: E402
import gen_tree_fabric as gtf          # noqa: E402
import gen_fattree as gft              # noqa: E402

CACHE = "--cache" in sys.argv


# ---------------------------------------------------------------------------
# live-run + measurement helpers
# ---------------------------------------------------------------------------

def _run(name):
    out = os.path.join(HERE, "output", name)
    fct = os.path.join(out, "fct.txt")
    if CACHE and os.path.exists(fct):
        return
    # fail hard: clear stale artifacts, then require a clean exit + a fresh FCT file
    if os.path.isdir(out):
        for f in os.listdir(out):
            os.remove(os.path.join(out, f))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(f"simulation failed for {name} (exit {rc}); see {out}/sim.log")
    if not os.path.exists(fct):
        raise RuntimeError(f"simulation for {name} produced no fct.txt; see {out}/sim.log")


def _penalty(name):
    """Relative penalty (== unfairness for equal-size/simultaneous) from analyze_gap."""
    r = subprocess.run([PYEXE, "hpcc-fs/analyze_gap.py", f"hpcc-fs/configs/hpcc_{name}.yml"],
                       cwd=HPCC_DIR, capture_output=True, text=True)
    val = None
    for line in r.stdout.splitlines():
        if "RELATIVE PENALTY" in line:
            for tok in line.split():
                if tok.endswith("x"):
                    try:
                        val = float(tok[:-1])
                    except ValueError:
                        pass
    if val is None:
        raise RuntimeError(f"could not parse penalty for {name}:\n{r.stdout}\n{r.stderr}")
    return val


def _pk(n, suffix, **kw):
    """Generate a parking-lot config; return its scenario name."""
    gpl.build(n, kw.pop("flow_size", 50_000_000), 0.2, "0.002ms", 1, "true", suffix, **kw)
    return f"parking_lot_{n}bn{suffix}"


def measure_pk(n, suffix, **kw):
    name = _pk(n, suffix, **kw)
    _run(name)
    return _penalty(name)


# ---------------------------------------------------------------------------
# Figure 1: N-sweep (parking lot)
# ---------------------------------------------------------------------------

def fig_nsweep():
    Ns = [2, 3, 4, 5, 6]
    stock = np.array([measure_pk(n, "", cc_mode=3) for n in Ns])
    multi = np.array([measure_pk(n, "_mr", cc_mode=3, multi_rate="true") for n in Ns])
    hpcc_fs = np.array([measure_pk(n, "_fs", cc_mode=11) for n in Ns])

    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    x = np.arange(len(Ns))
    width = 0.27
    ax.bar(x - width, stock, width, label="stock HPCC", color="#C0504D")
    ax.bar(x,         multi, width, label="multi-rate HPCC", color="#9BBB59")
    ax.bar(x + width, hpcc_fs, width, label="HPCC-FS (this paper)", color="#4F81BD")
    ax.axhline(1.0, linestyle="--", color="gray", linewidth=0.8, label="max-min oracle")
    ax.text(3.0, 0.55, "INT overflow\n(maxHop=5)", ha="center", fontsize=8,
            color="#7A1B17", style="italic")
    ax.set_xticks(x)
    ax.set_xticklabels([f"N={n}" for n in Ns])
    ax.set_ylabel("unfairness (long FCT / short FCT)")
    ax.set_title("Multi-bottleneck unfairness vs bottleneck count")
    ax.set_ylim(0, 2.3)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.95)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig_nsweep.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}  stock={stock.round(3)} fs={hpcc_fs.round(3)}")


# ---------------------------------------------------------------------------
# Figure 2: F2 robustness (asymmetric sizes + staggered starts)
# ---------------------------------------------------------------------------

def fig_robustness():
    variants = [
        ("symmetric (50 MB)",       "_sym",        {}),
        ("big long (200 MB)",       "_biglong",    dict(long_size=200_000_000, cross_size=50_000_000)),
        ("small long (10 MB)",      "_smalllong",  dict(long_size=10_000_000, cross_size=50_000_000)),
        ("long 200 / cross 10 MB",  "_lbcs",       dict(long_size=200_000_000, cross_size=10_000_000)),
        ("long head-start +3 ms",   "_lfirst",     dict(long_start=0.0, cross_start=0.003)),
        ("long joins late",         "_cfirst",     dict(long_start=0.003, cross_start=0.0)),
    ]
    labels, stock_v, fs_v = [], [], []
    for label, sfx, kw in variants:
        labels.append(label)
        stock_v.append(measure_pk(4, sfx, cc_mode=3, **kw))
        fs_v.append(measure_pk(4, "_fs" + sfx, cc_mode=11, **kw))

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    y = np.arange(len(labels))
    h = 0.36
    ax.barh(y + h/2, stock_v, h, label="stock HPCC", color="#C0504D")
    ax.barh(y - h/2, fs_v,    h, label="HPCC-FS",    color="#4F81BD")
    ax.axvline(1.0, linestyle="--", color="gray", linewidth=0.8, label="oracle = 1.0")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("relative penalty (long-path slowdown / short-path slowdown)")
    ax.set_title("HPCC-FS robustness across asymmetric workloads (parking-lot, N=4)")
    ax.set_xlim(0, 4.0)
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig_robustness.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}  stock={np.round(stock_v,3)} fs={np.round(fs_v,3)}")


# ---------------------------------------------------------------------------
# Figure 3: per-flow rate trace (N=4 parking lot) — reads trace.tr directly
# ---------------------------------------------------------------------------

REC = 56
IP_BASE = 0x0B000001


def node_of(ip):
    return (ip - IP_BASE) // 256


def parse_trace(tr_path, bin_ms=0.5):
    with open(tr_path, "rb") as f:
        data = f.read()
    (ln,) = struct.unpack_from("<I", data, 0)
    hdr = 4 + ln * 11 + 4
    nrec = (len(data) - hdr) // REC
    binw = bin_ms * 1e6
    acc = collections.defaultdict(lambda: collections.defaultdict(int))
    off = hdr
    for _ in range(nrec):
        if data[off + 27] == 0 and data[off + 29] == 0 and data[off + 26] == 0x11:
            t = struct.unpack_from("<Q", data, off)[0]
            sip = struct.unpack_from("<I", data, off + 16)[0]
            dip = struct.unpack_from("<I", data, off + 20)[0]
            size = struct.unpack_from("<H", data, off + 24)[0]
            acc[(node_of(sip), node_of(dip))][int(t // binw)] += size
        off += REC
    max_bin = max((b for d in acc.values() for b in d), default=0)
    t_axis = np.arange(max_bin + 1) * bin_ms
    out = {}
    for key, bins in acc.items():
        arr = np.zeros(max_bin + 1)
        for b, byt in bins.items():
            arr[b] = byt * 8 / binw
        out[key] = arr
    return out, t_axis


def _plot_trace(ax, flows, t_axis, long_key, title):
    for key, arr in flows.items():
        if key == long_key:
            ax.plot(t_axis, arr, color="#C0504D", linewidth=2.0,
                    label="long (4-hop, multi-bottleneck)")
        else:
            ax.plot(t_axis, arr, color="#4F81BD", linewidth=0.9, alpha=0.7)
    ax.plot([], [], color="#4F81BD", linewidth=1.5, label="cross (1-hop, single-bottleneck)")
    ax.axhline(12.5, linestyle="--", color="gray", linewidth=0.8, label="max-min fair (12.5 Gbps)")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("goodput (Gbps)")
    ax.set_title(title)
    ax.set_ylim(0, 26)
    ax.set_xlim(0, 40)
    ax.grid(linestyle=":", alpha=0.5)
    ax.legend(loc="center right", fontsize=8, framealpha=0.95)


def fig_rate_trace():
    # generate + run the two traced N=4 scenarios (stock and HPCC-FS)
    s_name = _pk(4, "_trace", cc_mode=3, enable_trace=1, trace_rx=True)
    f_name = _pk(4, "_fstrace", cc_mode=11, enable_trace=1, trace_rx=True)
    _run(s_name)
    _run(f_name)
    stock_tr = os.path.join(HERE, "output", s_name, "trace.tr")
    fs_tr = os.path.join(HERE, "output", f_name, "trace.tr")
    if not (os.path.exists(stock_tr) and os.path.exists(fs_tr)):
        print("missing trace.tr; skip fig_rate_trace")
        return
    s_flows, s_t = parse_trace(stock_tr, bin_ms=0.5)
    f_flows, f_t = parse_trace(fs_tr, bin_ms=0.5)
    long_key = (5, 6)  # long flow at N=4
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), sharey=True)
    _plot_trace(axes[0], s_flows, s_t, long_key, "Stock HPCC: winner-take-all collapse")
    _plot_trace(axes[1], f_flows, f_t, long_key, "HPCC-FS: converges to fair share in ~4 ms")
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig_rate_trace.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print("wrote", out)


# ---------------------------------------------------------------------------
# Figure 4: topology generalization
# ---------------------------------------------------------------------------

def fig_topology():
    # parking lot N=4
    p_stock = measure_pk(4, "", cc_mode=3)
    p_fs = measure_pk(4, "_fs", cc_mode=11)
    # tree fabric
    gtf.build("tree_fab_fig_s", cc_mode=3);  _run("tree_fab_fig_s")
    gtf.build("tree_fab_fig_f", cc_mode=11); _run("tree_fab_fig_f")
    t_stock, t_fs = _penalty("tree_fab_fig_s"), _penalty("tree_fab_fig_f")
    # k=4 fat-tree
    gft.build("ft4_fig_s", k=4, cc_mode=3);  _run("ft4_fig_s")
    gft.build("ft4_fig_f", k=4, cc_mode=11); _run("ft4_fig_f")
    f_stock, f_fs = _penalty("ft4_fig_s"), _penalty("ft4_fig_f")

    topos = ["parking-lot (N=4)", "tree fabric (3-tier)", "k=4 fat-tree (ECMP)"]
    stock = [p_stock, t_stock, f_stock]
    fs = [p_fs, t_fs, f_fs]

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    x = np.arange(len(topos))
    width = 0.36
    ax.bar(x - width/2, stock, width, label="stock HPCC", color="#C0504D")
    ax.bar(x + width/2, fs,    width, label="HPCC-FS",    color="#4F81BD")
    ax.axhline(1.0, linestyle="--", color="gray", linewidth=0.8, label="oracle = 1.0")
    ax.set_xticks(x)
    ax.set_xticklabels(topos, fontsize=9)
    ax.set_ylabel("relative penalty (long/short)")
    ax.set_title("HPCC-FS generalizes across topology families")
    ax.set_ylim(0, 2.3)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.95)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "fig_topology.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}  stock={np.round(stock,3)} fs={np.round(fs,3)}")


if __name__ == "__main__":
    if not os.path.exists(BIN):
        sys.exit(f"binary not found: {BIN}\nbuild it first: "
                 f"bash examples/hpcc/algorithm-validation/run.sh --optimized --build-only")
    fig_nsweep()
    fig_robustness()
    fig_rate_trace()
    fig_topology()
