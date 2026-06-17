#!/usr/bin/env python3
"""Topology diagrams for the paper's evaluation section.

Writes three PNGs into ./figures/:
  fig_topo_parking.png  — parking-lot at N=4 (one long flow + four cross flows)
  fig_topo_tree.png     — 3-tier tree fabric (1 core, 2 aggs, 4 edges, 8 hosts)
  fig_topo_fattree.png  — k=4 ECMP fat-tree (4 cores, 8 aggs, 8 edges, 16 hosts)

Design goals (kept readable at column width):
  * figure aspect matches the data bounds so equal-aspect drawing fills the canvas
    (no wasted margins);
  * legends sit in a horizontal strip at the bottom (they do not steal drawing width);
  * generous node radii / font sizes; 200 DPI.

Run:  venv/bin/python examples/hpcc/hpcc-fs/make_topology_figures.py
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

DPI = 200

# ── Visual constants ─────────────────────────────────────────────────────────
NODE_COLORS = {
    "core":   "#C0504D",  # red
    "agg":    "#8064A2",  # purple
    "edge":   "#4BACC6",  # cyan
    "switch": "#4F81BD",  # blue (generic / parking-lot)
    "host":   "#9BBB59",  # green
}
BOTTLENECK_COLOR = "#C0504D"
HOST_LINK_COLOR  = "#9E9E9E"
LONG_PATH_COLOR  = "#1F4E79"

R_NODE = 0.28   # switch / core / agg / edge radius
R_HOST = 0.22   # labelled host radius
NODE_FS = 15    # node label font
TIER_FS = 18    # tier label font
TITLE_FS = 21
LEGEND_FS = 15


def _node(ax, x, y, label, kind, r=R_NODE, fontsize=NODE_FS):
    c = NODE_COLORS[kind]
    ax.add_patch(plt.Circle((x, y), r, facecolor=c, edgecolor="black",
                            linewidth=0.8, zorder=3))
    if label:
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, color="white", zorder=4, fontweight="bold")


def _link(ax, x1, y1, x2, y2, color=HOST_LINK_COLOR, lw=1.0, ls="-", z=1):
    ax.plot([x1, x2], [y1, y2], linestyle=ls, color=color, linewidth=lw, zorder=z)


def _bottom_legend(fig, ax, handles, ncol):
    """Horizontal legend below the axes — does not consume drawing width."""
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.04),
              ncol=ncol, fontsize=LEGEND_FS, framealpha=0.95, handlelength=1.4,
              borderpad=0.5, columnspacing=1.6)


def _finish(fig, ax, xlim, ylim, title, out_name, bottom=0.16):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=TITLE_FS, pad=10)
    fig.subplots_adjust(left=0.04, right=0.98, top=0.92, bottom=bottom)
    out = os.path.join(FIG_DIR, out_name)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print("wrote", out)


# ── Parking lot ──────────────────────────────────────────────────────────────

def fig_topo_parking(N=4):
    # data: x in [-1.6, N+1.6], y in [-1.0, 3.2] -> aspect ~ (N+3.2)/4.2
    fig, ax = plt.subplots(figsize=(14.0, 7.6))
    SW_Y = 1.6
    sw_xs = [float(i) for i in range(N + 1)]

    # Bottleneck links (red, thick)
    for i in range(N):
        _link(ax, sw_xs[i], SW_Y, sw_xs[i + 1], SW_Y,
              color=BOTTLENECK_COLOR, lw=3.4, z=1)
    ax.text((sw_xs[0] + sw_xs[-1]) / 2, SW_Y + 0.36,
            "25 Gbps inter-switch (bottleneck)",
            ha="center", fontsize=15, color=BOTTLENECK_COLOR)

    # Switches
    for i, x in enumerate(sw_xs):
        _node(ax, x, SW_Y, f"s{i}", kind="switch")

    # Long-flow source/destination hosts (at ends, same row as switches)
    _node(ax, -0.95, SW_Y, "$L_s$", kind="host")
    _node(ax, N + 0.95, SW_Y, "$L_d$", kind="host")
    _link(ax, -0.95, SW_Y, sw_xs[0], SW_Y)
    _link(ax, sw_xs[-1], SW_Y, N + 0.95, SW_Y)

    # Cross-flow hosts (below each pair of adjacent switches)
    HOST_Y = -0.1
    for i in range(N):
        cs_x = sw_xs[i] + 0.30
        cd_x = sw_xs[i + 1] - 0.30
        _node(ax, cs_x, HOST_Y, f"$c_{i}^s$", kind="host")
        _node(ax, cd_x, HOST_Y, f"$c_{i}^d$", kind="host")
        _link(ax, cs_x, HOST_Y, sw_xs[i], SW_Y)
        _link(ax, cd_x, HOST_Y, sw_xs[i + 1], SW_Y)
        # cross-flow arrow
        ax.annotate("", xy=(cd_x, HOST_Y - 0.34), xytext=(cs_x, HOST_Y - 0.34),
                    arrowprops=dict(arrowstyle="-|>", color="#4BACC6", lw=1.4),
                    annotation_clip=False)

    # Long-flow arc above the switch row
    ax.annotate("", xy=(N + 0.95, SW_Y + 0.62),
                xytext=(-0.95, SW_Y + 0.62),
                arrowprops=dict(arrowstyle="-|>", color=LONG_PATH_COLOR, lw=2.2,
                                connectionstyle="arc3,rad=-0.16"))
    ax.text(N / 2, SW_Y + 1.18,
            f"LONG flow crosses all {N} bottlenecks",
            ha="center", color=LONG_PATH_COLOR, fontsize=17, fontweight="bold")

    # Annotation: host-link rate
    ax.text(N / 2, HOST_Y - 0.72, "host links: 100 Gbps (not a bottleneck)",
            ha="center", fontsize=14, color=HOST_LINK_COLOR, style="italic")

    legend = [
        mpatches.Patch(color=NODE_COLORS["switch"], label="switch"),
        mpatches.Patch(color=NODE_COLORS["host"],   label="host"),
        mpatches.Patch(color=BOTTLENECK_COLOR,      label="25 Gbps bottleneck"),
        mpatches.Patch(color="#4BACC6",             label="single-bottleneck cross flow"),
    ]
    _bottom_legend(fig, ax, legend, ncol=4)

    _finish(fig, ax, (-1.8, N + 1.8), (-1.2, SW_Y + 1.7),
            f"Parking lot at N={N}: one LONG flow + one CROSS flow per bottleneck",
            "fig_topo_parking.png", bottom=0.14)


# ── 3-tier tree fabric (15 nodes) ────────────────────────────────────────────

def fig_topo_tree():
    """Matches gen_tree_fabric.py: 1 core (0), 2 aggs (1,2), 4 edges (3-6),
    8 hosts (7-14). LONG flow 7 -> 13 highlighted."""
    fig, ax = plt.subplots(figsize=(13.0, 7.8))
    Y_CORE, Y_AGG, Y_EDGE, Y_HOST = 3.0, 2.0, 1.0, 0.0

    pos = {
        0:  (3.0, Y_CORE),
        1:  (1.5, Y_AGG),  2: (4.5, Y_AGG),
        3:  (0.5, Y_EDGE), 4: (2.3, Y_EDGE), 5: (3.7, Y_EDGE), 6: (5.5, Y_EDGE),
        7:  (0.15, Y_HOST), 8: (0.85, Y_HOST),
        9:  (1.95, Y_HOST), 10: (2.65, Y_HOST),
        11: (3.35, Y_HOST), 12: (4.05, Y_HOST),
        13: (5.15, Y_HOST), 14: (5.85, Y_HOST),
    }
    kinds = {0: "core", 1: "agg", 2: "agg",
             3: "edge", 4: "edge", 5: "edge", 6: "edge"}
    for h in range(7, 15):
        kinds[h] = "host"

    links = [
        (0, 1, "bn"), (0, 2, "bn"),
        (1, 3, "bn"), (1, 4, "bn"), (2, 5, "bn"), (2, 6, "bn"),
        (3, 7, "host"), (3, 8, "host"), (4, 9, "host"), (4, 10, "host"),
        (5, 11, "host"), (5, 12, "host"), (6, 13, "host"), (6, 14, "host"),
    ]
    for (a, b, k) in links:
        x1, y1 = pos[a]; x2, y2 = pos[b]
        if k == "bn":
            _link(ax, x1, y1, x2, y2, color=BOTTLENECK_COLOR, lw=2.8)
        else:
            _link(ax, x1, y1, x2, y2, lw=1.0)

    # Highlight LONG flow path: 7 -> 3 -> 1 -> 0 -> 2 -> 6 -> 13
    LONG = [7, 3, 1, 0, 2, 6, 13]
    for a, b in zip(LONG, LONG[1:]):
        x1, y1 = pos[a]; x2, y2 = pos[b]
        ax.plot([x1, x2], [y1, y2], color=LONG_PATH_COLOR, linewidth=3.2,
                solid_capstyle="round", zorder=2, alpha=0.6)

    for n, (x, y) in pos.items():
        _node(ax, x, y, str(n), kind=kinds[n],
              r=R_NODE if kinds[n] != "host" else R_HOST)

    for ylabel, yy in [("core", Y_CORE), ("agg", Y_AGG), ("edge", Y_EDGE), ("host", Y_HOST)]:
        ax.text(-0.5, yy, ylabel, ha="right", va="center",
                fontsize=TIER_FS, style="italic", color="gray")

    legend = [
        mpatches.Patch(color=NODE_COLORS["core"], label="core"),
        mpatches.Patch(color=NODE_COLORS["agg"],  label="agg"),
        mpatches.Patch(color=NODE_COLORS["edge"], label="edge"),
        mpatches.Patch(color=NODE_COLORS["host"], label="host"),
        plt.Line2D([0], [0], color=LONG_PATH_COLOR, lw=3.2, alpha=0.6,
                   label="LONG flow 7→13 (4 switch hops)"),
    ]
    _bottom_legend(fig, ax, legend, ncol=5)

    _finish(fig, ax, (-1.3, 6.5), (-0.6, 3.5),
            "Tree fabric (3-tier, 15 nodes, unique shortest paths — no ECMP)",
            "fig_topo_tree.png", bottom=0.13)


# ── k-ary ECMP fat-tree ──────────────────────────────────────────────────────

def fig_topo_fattree(k=4):
    half = k // 2
    n_core = half * half
    n_pods = k

    Y_CORE, Y_AGG, Y_EDGE, Y_HOST = 3.2, 2.2, 1.2, 0.2
    POD_WIDTH = 2.6
    figure_width = n_pods * POD_WIDTH
    pod_center = lambda p: (p + 0.5) * POD_WIDTH
    core_xs = [(i + 0.5) * (figure_width / n_core) for i in range(n_core)]

    # figure aspect matched to data bounds: width ~ figure_width+2, height ~ 4.6
    data_w = figure_width + 2.0
    data_h = (Y_CORE + 0.6) - (Y_HOST - 0.8)
    fig_w = 17.5
    fig_h = fig_w * (data_h / data_w) + 1.4   # +room for title & bottom legend
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    pos, kinds = {}, {}
    for c in range(n_core):
        pos[c] = (core_xs[c], Y_CORE); kinds[c] = "core"

    def agg_id(p, i):  return n_core + p * half + i
    def edge_id(p, j): return n_core + n_pods * half + p * half + j
    def host_id(p, j, h):
        return n_core + n_pods * half + n_pods * half + (p * half + j) * half + h

    for p in range(n_pods):
        cx = pod_center(p)
        agg_xs = [cx + (i - (half - 1) / 2.0) * 0.62 for i in range(half)]
        edge_xs = [cx + (j - (half - 1) / 2.0) * 0.62 for j in range(half)]
        for i, x in enumerate(agg_xs):
            pos[agg_id(p, i)] = (x, Y_AGG); kinds[agg_id(p, i)] = "agg"
        for j, x in enumerate(edge_xs):
            pos[edge_id(p, j)] = (x, Y_EDGE); kinds[edge_id(p, j)] = "edge"
            for h in range(half):
                hx = x + (h - (half - 1) / 2.0) * 0.26
                pos[host_id(p, j, h)] = (hx, Y_HOST); kinds[host_id(p, j, h)] = "host"

    # Links (drawn faint, behind nodes)
    for p in range(n_pods):
        for i in range(half):
            for c in range(i * half, (i + 1) * half):
                x1, y1 = pos[agg_id(p, i)]; x2, y2 = pos[c]
                _link(ax, x1, y1, x2, y2, lw=0.5, color="#777777", z=0)
    for p in range(n_pods):
        for i in range(half):
            for j in range(half):
                x1, y1 = pos[agg_id(p, i)]; x2, y2 = pos[edge_id(p, j)]
                _link(ax, x1, y1, x2, y2, lw=0.7, color="#999999", z=0)
    for p in range(n_pods):
        for j in range(half):
            for h in range(half):
                x1, y1 = pos[edge_id(p, j)]; x2, y2 = pos[host_id(p, j, h)]
                _link(ax, x1, y1, x2, y2, lw=0.6, color=HOST_LINK_COLOR, z=0)

    # Highlight one cross-pod LONG flow path (pod 0 -> pod k/2, edge 0)
    src = host_id(0, 0, 0)
    dst = host_id(n_pods // 2, 0, 0)
    long_path = [src, edge_id(0, 0), agg_id(0, 0), 0,
                 agg_id(n_pods // 2, 0), edge_id(n_pods // 2, 0), dst]
    for a, b in zip(long_path, long_path[1:]):
        x1, y1 = pos[a]; x2, y2 = pos[b]
        ax.plot([x1, x2], [y1, y2], color=LONG_PATH_COLOR, linewidth=2.8,
                alpha=0.7, zorder=2)

    for n_id, (x, y) in pos.items():
        if kinds[n_id] == "host":
            ax.add_patch(plt.Circle((x, y), 0.15, facecolor=NODE_COLORS["host"],
                                    edgecolor="black", linewidth=0.6, zorder=3))
        else:
            _node(ax, x, y, str(n_id), kind=kinds[n_id], r=0.24, fontsize=12)

    for p in range(n_pods):
        ax.text(pod_center(p), Y_HOST - 0.55, f"pod {p}",
                ha="center", fontsize=15, color="gray", style="italic")
    for ylabel, yy in [("core", Y_CORE), ("agg", Y_AGG), ("edge", Y_EDGE), ("host", Y_HOST)]:
        ax.text(-0.5, yy, ylabel, ha="right", va="center",
                fontsize=TIER_FS, style="italic", color="gray")

    legend = [
        mpatches.Patch(color=NODE_COLORS["core"], label="core"),
        mpatches.Patch(color=NODE_COLORS["agg"],  label="agg"),
        mpatches.Patch(color=NODE_COLORS["edge"], label="edge"),
        mpatches.Patch(color=NODE_COLORS["host"], label="host"),
        plt.Line2D([0], [0], color=LONG_PATH_COLOR, lw=2.8, alpha=0.7,
                   label="example inter-pod 5-switch path"),
    ]
    _bottom_legend(fig, ax, legend, ncol=5)

    _finish(fig, ax, (-1.2, figure_width + 0.6), (Y_HOST - 0.9, Y_CORE + 0.6),
            f"k = {k} ECMP fat-tree: {n_core} cores, {k * half} aggs, "
            f"{k * half} edges, {k * half * half} hosts",
            "fig_topo_fattree.png", bottom=0.14)


if __name__ == "__main__":
    fig_topo_parking()
    fig_topo_tree()
    fig_topo_fattree()
