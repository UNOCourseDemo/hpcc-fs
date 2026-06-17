#!/usr/bin/env bash
# Parallel runner for the repro-verification campaign (runs ON a VM).
# usage:  run_repro.sh <concurrency> <config_name> [config_name ...]
#   config_name = e.g. hpcc_ws_30  (no .yml); reads paper-simulations/configs/<name>.yml
# Each config runs the optimized binary into its own output dir; prints OK/FAIL per config.
set -u
CONC="${1:?concurrency required}"; shift
REPO=~/uno-hpcc-repro
HPCC="$REPO/examples/hpcc"
BIN="$REPO/build/examples/hpcc/ns3.45-hpcc-validation-optimized"
cd "$HPCC" || exit 1
printf '%s\n' "$@" | xargs -P "$CONC" -I{} bash -c '
  name="$1"
  out="paper-simulations/output/$name"
  mkdir -p "$out"
  /usr/bin/time -v "'"$BIN"'" "paper-simulations/configs/$name.yml" > "$out/sim.log" 2>&1
  rc=$?
  fct=$(wc -l < "$out/fct.txt" 2>/dev/null || echo 0)
  rss=$(awk "/Maximum resident/{print \$6}" "$out/sim.log")
  wall=$(awk "/Elapsed .wall/{print \$8}" "$out/sim.log")
  if [ "$rc" -eq 0 ] && [ "${fct:-0}" -gt 0 ]; then
    echo "OK   $name  fct=$fct  rss=${rss}KB  wall=$wall"
  else
    echo "FAIL $name  rc=$rc  fct=$fct  (see $out/sim.log)"
  fi
' _ {}
