#!/bin/bash
# =============================================================================
# Generate all traffic files for HPCC paper simulations
# Uses the refactored traffic_gen_uno with the project venv
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HPCC_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(cd "$HPCC_DIR/../.." && pwd)"
TRAFFIC_GEN="$HPCC_DIR/uno-hpcc/traffic_gen_uno/traffic_gen.py"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
OUTPUT_DIR="$SCRIPT_DIR/traffic"

# Paper parameters
NHOST=320
BANDWIDTH="100G"
TIME=0.1   # seconds of traffic

validate_traffic_file() {
    local file="$1"
    local host_count="$2"
    awk -v hosts="$host_count" -v file="$file" '
        function is_uint(value) { return value ~ /^[0-9]+$/ }
        function is_number(value) { return value ~ /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/ }
        function fail(message) { print "  ERROR: " message; errors++ }
        NR == 1 {
            gsub(/\r$/, "", $0)
            if (NF != 1 || !is_uint($1)) fail(file " header must be one unsigned integer")
            expected = $1 + 0
            next
        }
        /^[[:space:]]*$/ || /^[[:space:]]*#/ { next }
        {
            rows++
            if (NF != 6) {
                fail(file " line " NR " has " NF " columns, expected 6")
                next
            }
            if (!is_uint($1) || !is_uint($2) || !is_uint($3) || !is_uint($4) || !is_uint($5) || !is_number($6)) {
                fail(file " line " NR " has invalid fields")
                next
            }
            if ($1 >= hosts || $2 >= hosts) fail(file " line " NR " has src/dst outside host count " hosts)
            if ($1 == $2) fail(file " line " NR " has src == dst")
            if ($3 >= 8) fail(file " line " NR " has invalid priority group " $3)
            if ($5 <= 0) fail(file " line " NR " has non-positive flow size")
            start = $6 + 0.0
            if (rows > 1 && start + 1e-12 < last_start) fail(file " line " NR " is not sorted by start time")
            last_start = start
        }
        END {
            if (!errors && rows != expected) fail(file " header says " expected " flow(s), parsed " rows " data row(s)")
            if (!errors) print "  Validated " rows " flows"
            exit errors ? 1 : 0
        }
    ' "$file"
}

# Workloads and loads from the paper
WORKLOADS=("WEB_SEARCH" "FB_HDP")
WORKLOAD_TAGS=("ws" "fb")
LOADS=(0.3 0.5 0.7)
LOAD_TAGS=(30 50 70)

echo "============================================"
echo " HPCC Paper Traffic Generation"
echo "============================================"
echo "Python:    $VENV_PYTHON"
echo "Generator: $TRAFFIC_GEN"
echo "Output:    $OUTPUT_DIR"
echo "Hosts:     $NHOST"
echo "Bandwidth: $BANDWIDTH"
echo "Duration:  ${TIME}s"
echo ""

mkdir -p "$OUTPUT_DIR"

for w_idx in "${!WORKLOADS[@]}"; do
    workload="${WORKLOADS[$w_idx]}"
    w_tag="${WORKLOAD_TAGS[$w_idx]}"

    for l_idx in "${!LOADS[@]}"; do
        load="${LOADS[$l_idx]}"
        l_tag="${LOAD_TAGS[$l_idx]}"
        outfile="$OUTPUT_DIR/flow_${w_tag}_${l_tag}.txt"

        echo "Generating: ${w_tag}_${l_tag} (${workload}, load=${load})"
        "$VENV_PYTHON" "$TRAFFIC_GEN" \
            --conf "$HPCC_DIR/uno-hpcc/traffic_gen_uno/distributions/distributions.json" \
            --dist "$workload" \
            --nhost "$NHOST" \
            --load "$load" \
            --bandwidth "$BANDWIDTH" \
            --time "$TIME" \
            --output "$outfile"
        echo "  → $outfile"
        validate_traffic_file "$outfile" "$NHOST"
        echo ""
    done
done

echo "============================================"
echo " All traffic files generated in $OUTPUT_DIR"
echo "============================================"
ls -lh "$OUTPUT_DIR"/
