#!/usr/bin/env python3
"""HPCC-FS robustness experiments for the paper's defensibility pass.

Runs three experiment groups on the parking-lot benchmark and prints compact tables:
  1. window ablation     — FS rate-only (default) vs FS with the per-flow window cap on
  2. parameter sensitivity — sweep fs_alpha, fs_beta, fs_init_frac, min_rate at N=4
  3. PINT baseline        — cc_mode 10 on the N-sweep, as a comparison column

Must be run from the repo root (the binary + venv live there). Reuses gen_parking_lot.build()
and analyze_gap.py. Deterministic: same configs -> same artifacts.

Usage (from repo root):
  examples/hpcc/hpcc-fs is on sys.path; we shell out to the optimized binary + analyze_gap.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))                # examples/hpcc/hpcc-fs
HPCC_DIR = os.path.dirname(HERE)                                  # examples/hpcc (binary cwd)
REPO = os.path.dirname(os.path.dirname(HPCC_DIR))                 # repo root (uno-hpcc)
BIN = os.path.join(REPO, "build/examples/hpcc/ns3.45-hpcc-validation-optimized")
PY = os.path.join(REPO, "venv/bin/python")

sys.path.insert(0, HERE)
import gen_parking_lot as gpl  # noqa: E402


def run(name):
    """Run the binary on configs/hpcc_<name>.yml; outputs land under hpcc-fs/output/<name>/.

    Fails hard: clears stale artifacts, then requires a clean exit and a fresh fct.txt so we never
    parse leftover output from a previous (possibly failed) run.
    """
    out = os.path.join(HERE, "output", name)
    if os.path.isdir(out):
        for f in os.listdir(out):
            os.remove(os.path.join(out, f))
    os.makedirs(out, exist_ok=True)
    # binary expects to run from examples/hpcc (paths in yaml are relative to it)
    with open(os.path.join(out, "sim.log"), "w") as log:
        rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        raise RuntimeError(f"simulation failed for {name} (exit {rc}); see {out}/sim.log")
    if not os.path.exists(os.path.join(out, "fct.txt")):
        raise RuntimeError(f"simulation for {name} produced no fct.txt; see {out}/sim.log")


def metric(name):
    """Return (unfairness, pfc) for a finished run."""
    r = subprocess.run([PY, "hpcc-fs/analyze_gap.py", f"hpcc-fs/configs/hpcc_{name}.yml"],
                       cwd=HPCC_DIR, capture_output=True, text=True)
    unf = None
    for line in r.stdout.splitlines():
        if "UNFAIRNESS" in line or "RELATIVE PENALTY" in line:
            # take the x-suffixed number
            for tok in line.split():
                if tok.endswith("x"):
                    try:
                        unf = float(tok[:-1])
                    except ValueError:
                        pass
    pfc_file = os.path.join(HERE, "output", name, "pfc.txt")
    pfc = 0
    if os.path.exists(pfc_file):
        with open(pfc_file) as f:
            pfc = sum(1 for ln in f if ln.strip())
    return unf, pfc


def gen(name, **kw):
    """Generate a parking-lot config with overrides; returns the scenario name."""
    n = kw.pop("n")
    gpl.build(n, kw.pop("flow_size", 50_000_000), kw.pop("stop_time", 0.2),
              kw.pop("bn_delay", "0.002ms"), kw.pop("has_win", 1),
              kw.pop("var_win", "true"), kw.pop("suffix", ""),
              cc_mode=kw.pop("cc_mode", 11),
              fs_alpha=kw.pop("fs_alpha", 0.4), fs_beta=kw.pop("fs_beta", 0.226),
              fs_init_frac=kw.pop("fs_init_frac", 0.5),
              fs_disable_window=kw.pop("fs_disable_window", "true"),
              min_rate=kw.pop("min_rate", "1000Mb/s"))
    base = f"parking_lot_{n}bn"
    return base + kw.get("suffix_used", "")


def scenario(n, suffix, **kw):
    gpl.build(n, kw.get("flow_size", 50_000_000), kw.get("stop_time", 0.2),
              kw.get("bn_delay", "0.002ms"), kw.get("has_win", 1),
              kw.get("var_win", "true"), suffix,
              cc_mode=kw.get("cc_mode", 11),
              fs_alpha=kw.get("fs_alpha", 0.4), fs_beta=kw.get("fs_beta", 0.226),
              fs_init_frac=kw.get("fs_init_frac", 0.5),
              fs_disable_window=kw.get("fs_disable_window", "true"),
              min_rate=kw.get("min_rate", "1000Mb/s"))
    return f"parking_lot_{n}bn{suffix}"


def main():
    print("\n" + "=" * 68)
    print("  EXPERIMENT 1 — window ablation (N=2,3,4; FS rate-only vs window-on)")
    print("=" * 68)
    print(f"{'N':>3} {'FS rate-only':>14} {'FS window-on':>14}")
    for n in (2, 3, 4):
        off = scenario(n, "_fsab_off", cc_mode=11, fs_disable_window="true")
        on = scenario(n, "_fsab_on", cc_mode=11, fs_disable_window="false")
        run(off); run(on)
        uo, _ = metric(off); un, _ = metric(on)
        print(f"{n:>3} {str(uo)+'x':>14} {str(un)+'x':>14}")

    print("\n" + "=" * 68)
    print("  EXPERIMENT 2 — parameter sensitivity at N=4 (penalty, pfc)")
    print("=" * 68)
    base = scenario(4, "_fsbase", cc_mode=11)
    run(base)
    ub, pb = metric(base)
    print(f"  default (alpha=0.4,beta=0.226,init=0.5,minrate=1000Mb/s): {ub}x  pfc={pb}")
    print("  -- alpha --")
    for a in (0.2, 0.3, 0.5, 0.6):
        s = scenario(4, f"_a{a}", cc_mode=11, fs_alpha=a)
        run(s); u, p = metric(s); print(f"    alpha={a:<5} {u}x  pfc={p}")
    print("  -- beta --")
    for b in (0.1, 0.16, 0.3, 0.4):
        s = scenario(4, f"_b{b}", cc_mode=11, fs_beta=b)
        run(s); u, p = metric(s); print(f"    beta={b:<5}  {u}x  pfc={p}")
    print("  -- init_frac (startup C*frac) --")
    for fr in (0.25, 0.75, 1.0):
        s = scenario(4, f"_if{fr}", cc_mode=11, fs_init_frac=fr)
        run(s); u, p = metric(s); print(f"    init={fr:<5}  {u}x  pfc={p}")
    print("  -- min_rate --")
    for mr in ("100Mb/s", "500Mb/s", "2000Mb/s"):
        s = scenario(4, f"_mr{mr.replace('/','')}", cc_mode=11, min_rate=mr)
        run(s); u, p = metric(s); print(f"    min_rate={mr:<9} {u}x  pfc={p}")

    print("\n" + "=" * 68)
    print("  EXPERIMENT 3 — HPCC-PINT baseline (cc_mode 10) on N-sweep")
    print("=" * 68)
    print(f"{'N':>3} {'HPCC-PINT':>12}")
    for n in (2, 3, 4):
        s = scenario(n, "_pint", cc_mode=10)
        run(s); u, _ = metric(s); print(f"{n:>3} {str(u)+'x':>12}")

    print("\n" + "=" * 68)
    print("  EXPERIMENT 4 — cost on HPCC's home turf (single-bottleneck incast)")
    print("=" * 68)
    home_turf_incast()


def home_turf_incast():
    """Run the validated algorithm-validation incast under HPCC vs HPCC-FS (+ a higher startup
    rate) and report mean/tail FCT + peak queue. Builds the configs from the tracked incast
    config (algorithm-validation/configs/hpcc_incast.yml) by overriding cc_mode/min_rate/outputs.
    """
    base = os.path.join(HPCC_DIR, "algorithm-validation/configs/hpcc_incast.yml")
    with open(base) as f:
        tmpl = f.read()
    variants = [("HPCC      ", 3, None), ("HPCC-FS@1G", 11, "1000Mb/s"),
                ("HPCC-FS@5G", 11, "5000Mb/s"), ("HPCC-FS@8G", 11, "8000Mb/s")]
    print(f"  {'scheme':>10}  {'mean FCT':>9} {'tail FCT':>9} {'peak queue':>11}  pfc")
    for label, cc, mr in variants:
        name = f"incast_e4_cc{cc}{'_'+mr.replace('/','') if mr else ''}"
        out = os.path.join(HERE, "output", name)
        if os.path.isdir(out):
            for fl in os.listdir(out):
                os.remove(os.path.join(out, fl))
        os.makedirs(out, exist_ok=True)
        cfg = tmpl
        cfg = _set(cfg, "cc_mode", str(cc))
        if mr:
            cfg = _set(cfg, "min_rate", mr)
        for key, sub in [("trace_output_file", "trace.tr"), ("fct_output_file", "fct.txt"),
                         ("pfc_output_file", "pfc.txt"), ("bottleneck_output_file", "bottleneck.txt"),
                         ("qlen_mon_file", "qlen.txt")]:
            cfg = _set(cfg, key, f"hpcc-fs/output/{name}/{sub}")
        cfgpath = os.path.join(HERE, "configs", f"hpcc_{name}.yml")
        with open(cfgpath, "w") as f:
            f.write(cfg)
        with open(os.path.join(out, "sim.log"), "w") as log:
            rc = subprocess.run([BIN, f"hpcc-fs/configs/hpcc_{name}.yml"], cwd=HPCC_DIR,
                                stdout=log, stderr=subprocess.STDOUT).returncode
        if rc != 0 or not os.path.exists(os.path.join(out, "fct.txt")):
            raise RuntimeError(f"incast run failed for {name}; see {out}/sim.log")
        fcts = [int(l.split()[6]) for l in open(os.path.join(out, "fct.txt")) if l.split()]
        mean_us = sum(fcts) / len(fcts) / 1000
        tail_us = max(fcts) / 1000
        pq = "?"
        for l in open(os.path.join(out, "bottleneck.txt")):
            if l.startswith("max_overall"):
                pq = f"{round(int(l.split()[4])/1000)} KB"
        pfc = sum(1 for l in open(os.path.join(out, "pfc.txt")) if l.strip())
        print(f"  {label:>10}  {mean_us:7.1f}us {tail_us:7.1f}us {pq:>11}  {pfc}")


def _set(cfg, key, val):
    import re
    return re.sub(rf"(?m)^{re.escape(key)}:.*$", f"{key}: {val}", cfg)


if __name__ == "__main__":
    main()
