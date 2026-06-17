#!/usr/bin/env python3
"""
Generate YAML config files for all HPCC paper simulation runs.
5 CC schemes × 2 workloads × 3 loads = 30 configs.
"""
import os
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "configs")
os.makedirs(CONFIG_DIR, exist_ok=True)

# ── Fat-tree topology (from the paper repo) ─────────────────────
TOPOLOGY_FILE = "mix/fat.txt"

# ── Base parameters shared by all schemes ────────────────────────
BASE = {
    "enable_qcn": True,
    "use_dynamic_pfc_threshold": True,
    "pause_time": 5,
    "packet_payload_size": 1000,
    "l2_chunk_size": 4000,
    "l2_ack_interval": 1,
    "l2_back_to_zero": False,
    "topology_file": TOPOLOGY_FILE,
    "trace_file": "mix/trace.txt",
    "simulator_stop_time": 4.00,
    "clamp_target_rate": False,
    "fast_recovery_times": 1,
    "error_rate_per_link": 0.0,
    "global_t": 1,
    "multi_rate": False,
    "sample_feedback": False,
    "pint_log_base": 1.05,
    "pint_prob": 1.0,
    "rate_bound": True,
    "link_down": {"time": 0, "from_node": 0, "to_node": 0},
    "enable_trace": 0,
    "qlen_dump_interval": 100000000,
    "qlen_mon_interval": 100,
    "qlen_mon_start": 2000000000,
    "qlen_mon_end": 3000000000,
}

# ── BW-dependent parameters ─────────────────────────────────────
BW = 100  # Gbps

BUFFER_SIZE = int(16 * BW / 50)  # 32 MB at 100G

KMAX_MAP = {
    BW * 1_000_000_000: int(400 * BW / 25),
    BW * 4 * 1_000_000_000: int(400 * BW * 4 / 25),
}
KMIN_MAP = {
    BW * 1_000_000_000: int(100 * BW / 25),
    BW * 4 * 1_000_000_000: int(100 * BW * 4 / 25),
}
PMAX_MAP = {
    BW * 1_000_000_000: 0.2,
    BW * 4 * 1_000_000_000: 0.2,
}

# ── CC scheme definitions ────────────────────────────────────────
SCHEMES = {
    "hpcc": {
        "cc_mode": 3,
        "alpha_resume_interval": 1.0,
        "rate_decrease_interval": 4.0,
        "rp_timer": 300.0,
        "ewma_gain": 0.00390625,
        "rate_ai": f"{int(10 * BW / 25)}Mb/s",
        "rate_hai": f"{int(10 * BW / 25)}Mb/s",  # unused for HPCC
        "min_rate": "1000Mb/s",
        "dctcp_rate_ai": "1000Mb/s",
        "has_win": 1,
        "var_win": True,
        "fast_react": True,
        "u_target": 0.95,
        "mi_thresh": 0,
        "int_multi": int(BW / 25),
        "ack_high_prio": 0,
    },
    "dcqcn": {
        "cc_mode": 1,
        "alpha_resume_interval": 1.0,
        "rate_decrease_interval": 4.0,
        "rp_timer": 300.0,
        "ewma_gain": 0.00390625,
        "rate_ai": f"{int(5 * BW / 25)}Mb/s",
        "rate_hai": f"{int(50 * BW / 25)}Mb/s",
        "min_rate": "1000Mb/s",
        "dctcp_rate_ai": "1000Mb/s",
        "has_win": 0,
        "var_win": False,
        "fast_react": False,
        "u_target": 0.95,
        "mi_thresh": 0,
        "int_multi": 1,
        "ack_high_prio": 1,
    },
    "timely": {
        "cc_mode": 7,
        "alpha_resume_interval": 1.0,
        "rate_decrease_interval": 4.0,
        "rp_timer": 300.0,
        "ewma_gain": 0.00390625,
        "rate_ai": f"{int(10 * BW / 10)}Mb/s",
        "rate_hai": f"{int(50 * BW / 10)}Mb/s",
        "min_rate": "1000Mb/s",
        "dctcp_rate_ai": "1000Mb/s",
        "has_win": 0,
        "var_win": False,
        "fast_react": False,
        "u_target": 0.95,
        "mi_thresh": 0,
        "int_multi": 1,
        "ack_high_prio": 1,
    },
    "dctcp": {
        "cc_mode": 8,
        "alpha_resume_interval": 1.0,
        "rate_decrease_interval": 4.0,
        "rp_timer": 300.0,
        "ewma_gain": 0.0625,
        "rate_ai": "10Mb/s",
        "rate_hai": "10Mb/s",
        "min_rate": "1000Mb/s",
        "dctcp_rate_ai": "615Mb/s",
        "has_win": 1,
        "var_win": True,
        "fast_react": False,
        "u_target": 0.95,
        "mi_thresh": 0,
        "int_multi": 1,
        "ack_high_prio": 0,
    },
    "hpcc_pint": {
        "cc_mode": 10,
        "alpha_resume_interval": 1.0,
        "rate_decrease_interval": 4.0,
        "rp_timer": 300.0,
        "ewma_gain": 0.00390625,
        "rate_ai": f"{int(10 * BW / 25)}Mb/s",
        "rate_hai": f"{int(10 * BW / 25)}Mb/s",
        "min_rate": "1000Mb/s",
        "dctcp_rate_ai": "1000Mb/s",
        "has_win": 1,
        "var_win": True,
        "fast_react": True,
        "u_target": 0.95,
        "mi_thresh": 0,
        "int_multi": int(BW / 25),
        "ack_high_prio": 0,
        "pint_log_base": 1.05,
        "pint_prob": 1.0,
    },
}

# DCTCP uses different ECN thresholds (step-function marking)
DCTCP_KMAX = {
    BW * 1_000_000_000: int(30 * BW / 10),
    BW * 4 * 1_000_000_000: int(30 * BW * 4 / 10),
}
DCTCP_KMIN = DCTCP_KMAX.copy()  # Same as Kmax (step function)
DCTCP_PMAX = {
    BW * 1_000_000_000: 1.0,
    BW * 4 * 1_000_000_000: 1.0,
}

# ── Workloads and loads ──────────────────────────────────────────
WORKLOADS = {"ws": "Web Search", "fb": "Facebook Hadoop"}
LOADS = [30, 50, 70]


def build_config(scheme_name, workload_tag, load):
    """Build a complete YAML config dict for one simulation run."""
    scheme = SCHEMES[scheme_name]
    cfg = {}
    cfg.update(BASE)
    cfg.update(scheme)

    # File paths — output goes to per-run subdirectory
    traffic_dir = "paper-simulations/traffic"
    tag = f"{scheme_name}_{workload_tag}_{load}"
    output_dir = f"paper-simulations/output/{tag}"

    cfg["flow_file"] = f"{traffic_dir}/flow_{workload_tag}_{load}.txt"
    cfg["trace_output_file"] = f"{output_dir}/trace.tr"
    cfg["fct_output_file"] = f"{output_dir}/fct.txt"
    cfg["pfc_output_file"] = f"{output_dir}/pfc.txt"
    cfg["bottleneck_output_file"] = f"{output_dir}/bottleneck.txt"
    cfg["qlen_mon_file"] = f"{output_dir}/qlen.txt"

    # ECN thresholds — DCTCP uses different values
    if scheme_name == "dctcp":
        cfg["kmax_map"] = DCTCP_KMAX
        cfg["kmin_map"] = DCTCP_KMIN
        cfg["pmax_map"] = DCTCP_PMAX
    else:
        cfg["kmax_map"] = KMAX_MAP
        cfg["kmin_map"] = KMIN_MAP
        cfg["pmax_map"] = PMAX_MAP

    cfg["buffer_size"] = BUFFER_SIZE

    return cfg


def main():
    count = 0
    for scheme_name in SCHEMES:
        for w_tag in WORKLOADS:
            for load in LOADS:
                cfg = build_config(scheme_name, w_tag, load)
                filename = f"{scheme_name}_{w_tag}_{load}.yml"
                filepath = os.path.join(CONFIG_DIR, filename)

                # Add header comment
                header = (
                    f"# HPCC Paper Simulation Config\n"
                    f"# Scheme:   {scheme_name.upper()} (cc_mode={cfg['cc_mode']})\n"
                    f"# Workload: {WORKLOADS[w_tag]}\n"
                    f"# Load:     {load}%\n"
                    f"# Topology: {TOPOLOGY_FILE} (320 servers, fat-tree)\n"
                    f"# Bandwidth: {BW} Gbps\n\n"
                )

                with open(filepath, "w") as f:
                    f.write(header)
                    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

                count += 1
                print(f"  Created: {filename}")

    print(f"\nGenerated {count} config files in {CONFIG_DIR}/")


if __name__ == "__main__":
    main()
