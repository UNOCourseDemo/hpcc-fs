#!/usr/bin/env bash
# =============================================================================
# HPCC Paper Simulation — One-Shot Runner
# Generates traffic (if needed) and runs simulation(s) in a single command.
# Streams simulation output in real-time and captures exit codes.
#
# Usage:
#   bash run.sh configs/hpcc_ws_50.yml              # Single config
#   bash run.sh configs/hpcc_*.yml                   # Glob pattern
#   bash run.sh configs/dcqcn_fb_30.yml configs/timely_fb_30.yml
#   bash run.sh                                      # ALL configs
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HPCC_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(cd "$HPCC_DIR/../.." && pwd)"
BINARY_DEBUG="$PROJECT_ROOT/build/examples/hpcc/ns3.45-hpcc-validation-debug"
BINARY_RELEASE="$PROJECT_ROOT/build/examples/hpcc/ns3.45-hpcc-validation"
BINARY_OPTIMIZED="$PROJECT_ROOT/build/examples/hpcc/ns3.45-hpcc-validation-optimized"
BINARY_PROFILE="${HPCC_BINARY_PROFILE:-debug}"
BINARY_OVERRIDE="${HPCC_BINARY:-}"
BINARY=""
CONFIG_DIR="$SCRIPT_DIR/configs"
OUTPUT_ROOT="$SCRIPT_DIR/output"
TRAFFIC_DIR="$SCRIPT_DIR/traffic"
BUILD_BEFORE_RUN="${HPCC_BUILD:-0}"
AUTO_BUILD_MISSING="${HPCC_AUTO_BUILD:-1}"
BUILD_ONLY=0
BUILD_ALL=0
RECONFIGURE=0
TRAFFIC_ONLY=0
CHECK_INPUTS_ONLY=0
FORCE_TRAFFIC=0
BUILD_JOBS="${HPCC_BUILD_JOBS:-14}"
if [ -n "${HPCC_CMAKE:-}" ]; then
    CMAKE_BIN="$HPCC_CMAKE"
elif [ -n "${HOME:-}" ] && [ -x "$HOME/Applications/CLion.app/Contents/bin/cmake/mac/aarch64/bin/cmake" ]; then
    CMAKE_BIN="$HOME/Applications/CLion.app/Contents/bin/cmake/mac/aarch64/bin/cmake"
elif [ -x /opt/homebrew/bin/cmake ]; then
    CMAKE_BIN="/opt/homebrew/bin/cmake"
else
    CMAKE_BIN="cmake"
fi

# ── Traffic generation settings ─────────────────────────────────
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
TRAFFIC_GEN="$HPCC_DIR/uno-hpcc/traffic_gen_uno/traffic_gen.py"
DIST_JSON="$HPCC_DIR/uno-hpcc/traffic_gen_uno/distributions/distributions.json"
NHOST=320
BANDWIDTH="100G"
TRAFFIC_DURATION=0.1  # seconds

usage() {
    cat <<EOF
Usage: $0 [--debug|--release|--optimized] [--build] [--build-only|--build-all] [--binary PATH] [config.yml ...]

Binary selection:
  --debug       Use ns3.45-hpcc-validation-debug (default)
  --release     Use ns3.45-hpcc-validation
  --optimized   Use ns3.45-hpcc-validation-optimized
  --binary PATH Use an explicit hpcc-validation executable

Build options:
  --build       Configure/build the selected profile before running
  --build-only  Configure/build the selected profile, then exit
  --build-all   Configure/build debug, release, and optimized profiles, then exit
  --reconfigure Run CMake configure even when CMakeCache.txt already exists
  --traffic-only
                Generate/repair traffic for the selected configs, then exit
  --check-inputs
                Validate selected config inputs without generating or running
  --force-traffic
                Regenerate selected traffic files even when they validate
  --no-auto-build
                Do not auto-build if the selected profile binary is missing

Environment:
  HPCC_BINARY_PROFILE=debug|release|optimized
  HPCC_BINARY=/absolute/path/to/hpcc-validation-binary
  HPCC_BUILD=1
  HPCC_AUTO_BUILD=0
  HPCC_BUILD_JOBS=14
  HPCC_CMAKE=/path/to/cmake
EOF
}

CONFIG_ARGS=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        --debug)
            BINARY_PROFILE="debug"
            ;;
        --release)
            BINARY_PROFILE="release"
            ;;
        --optimized)
            BINARY_PROFILE="optimized"
            ;;
        --binary)
            shift
            if [ "$#" -eq 0 ]; then
                echo "ERROR: --binary requires a path"
                exit 2
            fi
            BINARY_OVERRIDE="$1"
            ;;
        --build)
            BUILD_BEFORE_RUN=1
            ;;
        --build-only)
            BUILD_BEFORE_RUN=1
            BUILD_ONLY=1
            ;;
        --build-all)
            BUILD_ALL=1
            BUILD_ONLY=1
            ;;
        --reconfigure)
            RECONFIGURE=1
            ;;
        --traffic-only)
            TRAFFIC_ONLY=1
            ;;
        --check-inputs)
            CHECK_INPUTS_ONLY=1
            ;;
        --force-traffic)
            FORCE_TRAFFIC=1
            ;;
        --no-auto-build)
            AUTO_BUILD_MISSING=0
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            while [ "$#" -gt 0 ]; do
                CONFIG_ARGS+=("$1")
                shift
            done
            break
            ;;
        -*)
            echo "ERROR: Unknown option: $1"
            usage
            exit 2
            ;;
        *)
            CONFIG_ARGS+=("$1")
            ;;
    esac
    shift
done
if [ "${#CONFIG_ARGS[@]}" -gt 0 ]; then
    set -- "${CONFIG_ARGS[@]}"
else
    set --
fi

select_binary() {
    if [ -n "$BINARY_OVERRIDE" ]; then
        BINARY="$BINARY_OVERRIDE"
        return
    fi

    case "$BINARY_PROFILE" in
        debug)
            BINARY="$BINARY_DEBUG"
            ;;
        release)
            BINARY="$BINARY_RELEASE"
            ;;
        optimized)
            BINARY="$BINARY_OPTIMIZED"
            ;;
        *)
            echo "ERROR: Unknown HPCC binary profile: $BINARY_PROFILE"
            usage
            exit 2
            ;;
    esac
}

select_binary

build_dir_for_profile() {
    case "$1" in
        debug)
            echo "$PROJECT_ROOT/cmake-build-debug"
            ;;
        release)
            echo "$PROJECT_ROOT/cmake-build-release"
            ;;
        optimized)
            echo "$PROJECT_ROOT/cmake-build-optimized"
            ;;
        *)
            echo "ERROR: Unknown build profile: $1" >&2
            return 2
            ;;
    esac
}

configure_profile() {
    local profile="$1"
    local build_dir="$2"

    case "$profile" in
        debug)
            "$CMAKE_BIN" -S "$PROJECT_ROOT" -B "$build_dir" \
                -DCMAKE_BUILD_TYPE=Debug \
                -DNS3_NATIVE_OPTIMIZATIONS=OFF \
                -DNS3_EXAMPLES=ON \
                -DNS3_WARNINGS_AS_ERRORS=OFF
            ;;
        release)
            "$CMAKE_BIN" -S "$PROJECT_ROOT" -B "$build_dir" \
                -DCMAKE_BUILD_TYPE=Release \
                -DNS3_NATIVE_OPTIMIZATIONS=OFF \
                -DNS3_EXAMPLES=ON \
                -DNS3_WARNINGS_AS_ERRORS=OFF
            ;;
        optimized)
            "$CMAKE_BIN" -S "$PROJECT_ROOT" -B "$build_dir" \
                -DCMAKE_BUILD_TYPE=Release \
                -DNS3_NATIVE_OPTIMIZATIONS=ON \
                -DNS3_EXAMPLES=ON \
                -DNS3_WARNINGS_AS_ERRORS=OFF
            ;;
    esac
}

build_profile() {
    local profile="$1"
    local build_dir
    build_dir="$(build_dir_for_profile "$profile")"

    echo "=============================================="
    echo "  Building hpcc-validation ($profile)"
    echo "=============================================="
    echo ""
    echo "  CMake:     $CMAKE_BIN"
    echo "  Build dir: $build_dir"
    echo "  Jobs:      $BUILD_JOBS"
    echo ""

    if [ -f "$build_dir/CMakeCache.txt" ] && [ "$RECONFIGURE" -eq 0 ]; then
        if grep -q '^NS3_WARNINGS_AS_ERRORS:BOOL=ON$' "$build_dir/CMakeCache.txt"; then
            echo "  Configure: updating existing CMakeCache.txt with NS3_WARNINGS_AS_ERRORS=OFF"
            configure_profile "$profile" "$build_dir"
        else
            echo "  Configure: existing CMakeCache.txt found; skipping configure"
            echo "             pass --reconfigure to regenerate this build directory"
        fi
    else
        configure_profile "$profile" "$build_dir"
    fi

    "$CMAKE_BIN" --build "$build_dir" --target hpcc-validation -j "$BUILD_JOBS"
    echo ""
}

if [ "$BUILD_ALL" -eq 1 ]; then
    build_profile debug
    build_profile release
    build_profile optimized
    exit 0
fi

if [ "$BUILD_BEFORE_RUN" -eq 1 ]; then
    if [ -n "$BINARY_OVERRIDE" ]; then
        echo "ERROR: --build cannot be combined with --binary"
        exit 2
    fi
    build_profile "$BINARY_PROFILE"
    select_binary
fi

if [ "$BUILD_ONLY" -eq 1 ]; then
    exit 0
fi

if [ "$TRAFFIC_ONLY" -eq 0 ] && [ "$CHECK_INPUTS_ONLY" -eq 0 ] \
    && [ ! -f "$BINARY" ] && [ -z "$BINARY_OVERRIDE" ] \
    && [ "$AUTO_BUILD_MISSING" = "1" ] && [ "$BUILD_BEFORE_RUN" -eq 0 ]; then
    echo "Selected $BINARY_PROFILE binary is missing; building it now."
    echo "Use --no-auto-build or HPCC_AUTO_BUILD=0 to disable this behavior."
    echo ""
    build_profile "$BINARY_PROFILE"
    select_binary
fi

# ── Lookup helpers ──────────────────────────────────────────────
get_dist_name() {
    case "$1" in
        ws) echo "WEB_SEARCH" ;;
        fb) echo "FB_HDP" ;;
        *)  echo "" ;;
    esac
}

get_load_fraction() {
    case "$1" in
        30) echo "0.3" ;;
        50) echo "0.5" ;;
        70) echo "0.7" ;;
        *)  echo "" ;;
    esac
}

config_value() {
    local key="$1"
    local file="$2"
    awk -F: -v key="$key" '
        $1 == key {
            value = $0
            sub("^[^:]*:", "", value)
            gsub(/^[ \t"]+|[ \t"]+$/, "", value)
            print value
            exit
        }
    ' "$file"
}

resolve_hpcc_path() {
    local path="$1"
    if [ -z "$path" ]; then
        echo ""
    elif [ "${path:0:1}" = "/" ]; then
        echo "$path"
    else
        echo "$HPCC_DIR/$path"
    fi
}

traffic_header_count() {
    awk 'NR == 1 {gsub(/\r/, "", $0); print $1; exit}' "$1"
}

validate_traffic_file() {
    local file="$1"
    local host_count="$2"

    if [ ! -f "$file" ]; then
        echo "  ERROR: Traffic file missing: $file"
        return 1
    fi

    awk -v hosts="$host_count" -v file="$file" '
        function is_uint(value) {
            return value ~ /^[0-9]+$/
        }
        function is_number(value) {
            return value ~ /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/
        }
        function fail(message) {
            print "  ERROR: Traffic: " message
            errors++
        }
        NR == 1 {
            gsub(/\r$/, "", $0)
            if (NF != 1 || !is_uint($1)) {
                fail(file " header must be one unsigned integer")
            } else {
                expected = $1 + 0
            }
            next
        }
        /^[[:space:]]*$/ || /^[[:space:]]*#/ { next }
        {
            gsub(/\r$/, "", $0)
            rows++
            if (NF != 6) {
                fail(file " line " NR " has " NF " columns, expected 6")
                next
            }
            if (!is_uint($1) || !is_uint($2) || !is_uint($3) || !is_uint($4) || !is_uint($5)) {
                fail(file " line " NR " has non-integer src/dst/pg/dport/size")
                next
            }
            if (!is_number($6)) {
                fail(file " line " NR " has non-numeric start time")
                next
            }
            if ($1 >= hosts || $2 >= hosts) {
                fail(file " line " NR " has src/dst outside host count " hosts)
            }
            if ($1 == $2) {
                fail(file " line " NR " has src == dst")
            }
            if ($3 >= 8) {
                fail(file " line " NR " has invalid priority group " $3)
            }
            if ($5 <= 0) {
                fail(file " line " NR " has non-positive flow size")
            }
            start = $6 + 0.0
            if (start < 0) {
                fail(file " line " NR " has negative start time")
            }
            if (rows > 1 && start + 1e-12 < last_start) {
                fail(file " line " NR " is not sorted by start time")
            }
            last_start = start
        }
        END {
            if (NR == 0) {
                fail(file " is empty")
            }
            if (!errors && rows != expected) {
                fail(file " header says " expected " flow(s), parsed " rows " data row(s)")
            }
            if (!errors) {
                print "  Traffic:  " file " validated (" rows " flows)"
            }
            exit errors ? 1 : 0
        }
    ' "$file"
}

validate_result_artifacts() {
    local run_output="$1"
    local flow_path="$2"
    local config="$3"
    local report="$run_output/validation_checks.txt"
    local errors=0
    local expected
    local fct_file="$run_output/fct.txt"
    local pfc_file="$run_output/pfc.txt"
    local qlen_file="$run_output/qlen.txt"
    local bottleneck_cfg
    local bottleneck_file
    local final_status

    : > "$report"
    expected="$(traffic_header_count "$flow_path")"

    if [ ! -f "$fct_file" ]; then
        echo "FAIL: missing FCT file: $fct_file" >> "$report"
        errors=$((errors + 1))
    else
        local fct_count
        fct_count=$(wc -l < "$fct_file" | tr -d ' ')
        if [ "$fct_count" != "$expected" ]; then
            echo "FAIL: FCT row count $fct_count != expected flow count $expected" >> "$report"
            errors=$((errors + 1))
        else
            echo "OK: FCT row count matched expected flow count $expected." >> "$report"
        fi
    fi

    if [ ! -f "$pfc_file" ]; then
        echo "FAIL: missing PFC file: $pfc_file" >> "$report"
        errors=$((errors + 1))
    else
        if awk '
            function is_uint(value) { return value ~ /^[0-9]+$/ }
            NF == 0 { next }
            {
                row++
                if (NF != 6) { errors++; next }
                for (i = 1; i <= 6; i++) if (!is_uint($i)) errors++
                if ($6 != 0 && $6 != 1) errors++
            }
            END { exit errors ? 1 : 0 }
        ' "$pfc_file"; then
            echo "OK: PFC schema check passed." >> "$report"
        else
            echo "FAIL: PFC schema check failed." >> "$report"
            errors=$((errors + 1))
        fi
    fi

    if [ ! -s "$qlen_file" ] || ! grep -q '^time:' "$qlen_file"; then
        echo "FAIL: qlen output missing or has no time blocks." >> "$report"
        errors=$((errors + 1))
    else
        echo "OK: qlen output contains sampled time blocks." >> "$report"
    fi

    bottleneck_cfg="$(config_value bottleneck_output_file "$config")"
    bottleneck_file="$run_output/$(basename "$bottleneck_cfg")"
    if [ -z "$bottleneck_cfg" ]; then
        echo "FAIL: config is missing bottleneck_output_file." >> "$report"
        errors=$((errors + 1))
    elif [ ! -s "$bottleneck_file" ] || ! grep -q '^max_overall ' "$bottleneck_file"; then
        echo "FAIL: bottleneck output missing or has no max_overall row." >> "$report"
        errors=$((errors + 1))
    else
        echo "OK: bottleneck output contains max_overall row." >> "$report"
    fi

    final_status="$(grep 'HPCC status' "$run_output/simulation.log" | tail -1 || true)"
    if [ -z "$final_status" ]; then
        echo "FAIL: simulation.log has no HPCC status line." >> "$report"
        errors=$((errors + 1))
    elif [[ "$final_status" =~ started=([0-9]+)/([0-9]+).*completed=([0-9]+).*pending=([0-9]+).*bytes_left=([0-9]+).*in_flight=([0-9]+) ]]; then
        local started="${BASH_REMATCH[1]}"
        local total="${BASH_REMATCH[2]}"
        local completed="${BASH_REMATCH[3]}"
        local pending="${BASH_REMATCH[4]}"
        local bytes_left="${BASH_REMATCH[5]}"
        local in_flight="${BASH_REMATCH[6]}"
        if [ "$started" = "$total" ] && [ "$completed" = "$total" ] \
            && [ "$pending" = "0" ] && [ "$bytes_left" = "0" ] && [ "$in_flight" = "0" ]; then
            echo "OK: final HPCC status drained all flows." >> "$report"
        else
            echo "FAIL: final HPCC status did not drain all flows: $final_status" >> "$report"
            errors=$((errors + 1))
        fi
    else
        echo "FAIL: could not parse final HPCC status: $final_status" >> "$report"
        errors=$((errors + 1))
    fi

    return "$errors"
}

# ── Preflight checks ───────────────────────────────────────────
if [ "$TRAFFIC_ONLY" -eq 0 ] && [ "$CHECK_INPUTS_ONLY" -eq 0 ] && [ ! -f "$BINARY" ]; then
    echo "ERROR: Simulation binary not found at:"
    echo "  $BINARY"
    echo ""
    echo "Selected profile: $BINARY_PROFILE"
    echo ""
    echo "Build it through this runner:"
    echo "  bash $0 --$BINARY_PROFILE --build $(printf '%q ' "$@")"
    echo ""
    echo "Or configure/build without ./ns3, for example:"
    echo "  /opt/homebrew/bin/cmake -S $PROJECT_ROOT -B $PROJECT_ROOT/cmake-build-optimized -DCMAKE_BUILD_TYPE=Release -DNS3_NATIVE_OPTIMIZATIONS=ON -DNS3_EXAMPLES=ON -DNS3_WARNINGS_AS_ERRORS=OFF"
    echo "  /opt/homebrew/bin/cmake --build $PROJECT_ROOT/cmake-build-optimized --target hpcc-validation -j 14"
    exit 1
fi

if [ "$CHECK_INPUTS_ONLY" -eq 0 ] && [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Python venv not found at: $VENV_PYTHON"
    exit 1
fi

if [ "$CHECK_INPUTS_ONLY" -eq 0 ] && [ ! -f "$TRAFFIC_GEN" ]; then
    echo "ERROR: Traffic generator not found at: $TRAFFIC_GEN"
    exit 1
fi

# ── Determine which configs to run ──────────────────────────────
if [ $# -gt 0 ]; then
    CONFIGS=()
    for c in "$@"; do
        if [ "${c:0:1}" = "/" ]; then
            CONFIGS+=("$c")
        else
            CONFIGS+=("$SCRIPT_DIR/$c")
        fi
    done
else
    CONFIGS=("$CONFIG_DIR"/*.yml)
fi

TOTAL=${#CONFIGS[@]}
if [ "$TOTAL" -eq 0 ]; then
    echo "ERROR: No config files found."
    exit 1
fi

# ── Helper: generate traffic if missing ─────────────────────────
generate_traffic() {
    local workload_tag="$1"
    local load_tag="$2"
    local outfile="$TRAFFIC_DIR/flow_${workload_tag}_${load_tag}.txt"

    if [ -f "$outfile" ] && [ "$FORCE_TRAFFIC" -eq 0 ]; then
        local flow_count
        flow_count=$(head -1 "$outfile" | tr -d ' ')
        echo "  Traffic:  flow_${workload_tag}_${load_tag}.txt exists ($flow_count flows)"
        if validate_traffic_file "$outfile" "$NHOST"; then
            return 0
        fi

        local backup="${outfile}.invalid.$(date +%Y%m%d-%H%M%S)"
        echo "  Traffic:  Existing file is invalid; moving it to $backup"
        mv "$outfile" "$backup"
    elif [ -f "$outfile" ]; then
        echo "  Traffic:  Regenerating flow_${workload_tag}_${load_tag}.txt (--force-traffic)"
    fi

    local dist
    dist=$(get_dist_name "$workload_tag")
    local load
    load=$(get_load_fraction "$load_tag")

    if [ -z "$dist" ]; then
        echo "  ERROR: Unknown workload tag '$workload_tag'"
        return 1
    fi
    if [ -z "$load" ]; then
        echo "  ERROR: Unknown load tag '$load_tag'"
        return 1
    fi

    mkdir -p "$TRAFFIC_DIR"
    echo "  Traffic:  Generating flow_${workload_tag}_${load_tag}.txt (${dist}, load=${load})..."

    "$VENV_PYTHON" "$TRAFFIC_GEN" \
        --conf "$DIST_JSON" \
        --dist "$dist" \
        --nhost "$NHOST" \
        --load "$load" \
        --bandwidth "$BANDWIDTH" \
        --time "$TRAFFIC_DURATION" \
        --output "$outfile" 2>&1 | sed 's/^/    /'

    echo "  Traffic:  Done"
    validate_traffic_file "$outfile" "$NHOST"
}

# ── Helper: parse workload and load from config filename ────────
parse_config_name() {
    local name
    name=$(basename "$1" .yml)
    LOAD_TAG=$(echo "$name" | awk -F'_' '{print $NF}')
    WORKLOAD_TAG=$(echo "$name" | awk -F'_' '{print $(NF-1)}')
    SCHEME_TAG=$(echo "$name" | sed "s/_${WORKLOAD_TAG}_${LOAD_TAG}$//")
}

# ── Main ────────────────────────────────────────────────────────
echo "=============================================="
echo "  HPCC Paper Simulation — One-Shot Run"
echo "=============================================="
echo ""
echo "  Binary:   $BINARY"
echo "  Profile:  $BINARY_PROFILE"
echo "  Configs:  $TOTAL file(s)"
echo "  Hosts:    $NHOST"
echo "  BW:       $BANDWIDTH"
echo "  Duration: ${TRAFFIC_DURATION}s traffic"
echo ""

CURRENT=0
FAILED=0
RESULT_LINES=""

for config in "${CONFIGS[@]}"; do
    CURRENT=$((CURRENT + 1))
    if [ ! -f "$config" ]; then
        echo "ERROR: Config not found: $config"
        RESULT_LINES="${RESULT_LINES}  FAIL $(basename "$config")  missing config\n"
        FAILED=$((FAILED + 1))
        continue
    fi

    NAME=$(basename "$config" .yml)
    RUN_OUTPUT="$OUTPUT_ROOT/$NAME"
    CFG_FLOW="$(config_value flow_file "$config")"
    FLOW_PATH="$(resolve_hpcc_path "$CFG_FLOW")"

    echo "----------------------------------------------"
    echo "[$CURRENT/$TOTAL] $NAME"
    echo "----------------------------------------------"

    # Step 1: Parse config name
    parse_config_name "$config"
    echo "  Scheme:   $SCHEME_TAG"
    echo "  Workload: $WORKLOAD_TAG"
    echo "  Load:     ${LOAD_TAG}%"

    # Step 2: Generate traffic if needed
    if [ "$CHECK_INPUTS_ONLY" -eq 1 ]; then
        if [ -z "$CFG_FLOW" ]; then
            echo "  ERROR: Config is missing flow_file"
            RESULT_LINES="${RESULT_LINES}  FAIL ${NAME}  missing flow_file\n"
            FAILED=$((FAILED + 1))
            echo ""
            continue
        fi
        if validate_traffic_file "$FLOW_PATH" "$NHOST"; then
            echo "  Result:   OK (input checks only)"
            RESULT_LINES="${RESULT_LINES}  OK   ${NAME}  input checks ok\n"
        else
            echo "  Result:   FAILED (input checks only)"
            RESULT_LINES="${RESULT_LINES}  FAIL ${NAME}  input checks failed\n"
            FAILED=$((FAILED + 1))
        fi
        echo ""
        continue
    fi

    generate_traffic "$WORKLOAD_TAG" "$LOAD_TAG"
    if [ -z "$CFG_FLOW" ] || ! validate_traffic_file "$FLOW_PATH" "$NHOST"; then
        echo "  Result:   FAILED (traffic validation failed for config flow_file)"
        RESULT_LINES="${RESULT_LINES}  FAIL ${NAME}  traffic validation failed\n"
        FAILED=$((FAILED + 1))
        echo ""
        continue
    fi

    if [ "$TRAFFIC_ONLY" -eq 1 ]; then
        echo "  Result:   OK (traffic only)"
        RESULT_LINES="${RESULT_LINES}  OK   ${NAME}  traffic ready\n"
        echo ""
        continue
    fi

    # Step 3: Create output directory and copy config for reproducibility
    mkdir -p "$RUN_OUTPUT"
    cp "$config" "$RUN_OUTPUT/config.yml"

    # Step 4: Run simulation — stream to terminal AND save to log
    echo "  Output:   $RUN_OUTPUT/"
    echo "  Sim:      Running..."
    echo ""

    cd "$HPCC_DIR"
    START_TIME=$(date +%s)

    # Use set +e so we capture the exit code instead of aborting
    set +e
    "$BINARY" "$config" 2>&1 | tee "$RUN_OUTPUT/simulation.log"
    SIM_EXIT=${PIPESTATUS[0]}
    set -e

    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    echo ""

    if [ "$SIM_EXIT" -eq 0 ]; then
        # Collect output files into the per-run directory
        CFG_FCT=$(grep "fct_output_file" "$config" | awk '{print $2}')
        CFG_PFC=$(grep "pfc_output_file" "$config" | awk '{print $2}')
        CFG_QLEN=$(grep "qlen_mon_file" "$config" | awk '{print $2}')
        CFG_TRACE=$(grep "trace_output_file" "$config" | awk '{print $2}')
        CFG_BOTTLENECK=$(config_value bottleneck_output_file "$config")

        for f in "$CFG_FCT" "$CFG_PFC" "$CFG_QLEN" "$CFG_TRACE" "$CFG_BOTTLENECK"; do
            if [ -n "$f" ] && [ -f "$HPCC_DIR/$f" ]; then
                cp "$HPCC_DIR/$f" "$RUN_OUTPUT/" 2>/dev/null || true
            fi
        done

        VALIDATION_EXIT=0
        set +e
        validate_result_artifacts "$RUN_OUTPUT" "$FLOW_PATH" "$config"
        VALIDATION_EXIT=$?
        set -e
        if [ -f "$RUN_OUTPUT/validation_checks.txt" ]; then
            sed 's/^/  /' "$RUN_OUTPUT/validation_checks.txt"
        fi

        # Count completed flows
        FLOW_COUNT="0"
        if [ -n "$CFG_FCT" ] && [ -f "$RUN_OUTPUT/$(basename "$CFG_FCT")" ]; then
            FLOW_COUNT=$(wc -l < "$RUN_OUTPUT/$(basename "$CFG_FCT")" | tr -d ' ')
        fi

        if [ "$VALIDATION_EXIT" -eq 0 ]; then
            echo "  Result:   OK (exit=0, ${ELAPSED}s, ${FLOW_COUNT} flows, validation checks ok)"
            RESULT_LINES="${RESULT_LINES}  OK   ${NAME}  ${ELAPSED}s  ${FLOW_COUNT} flows  checks=ok\n"
        else
            echo "  Result:   FAILED (exit=0, ${ELAPSED}s, ${FLOW_COUNT} flows, validation failed)"
            RESULT_LINES="${RESULT_LINES}  FAIL ${NAME}  validation failed\n"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "  Result:   FAILED (exit=$SIM_EXIT, ${ELAPSED}s)"
        RESULT_LINES="${RESULT_LINES}  FAIL ${NAME}  exit=$SIM_EXIT\n"
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

# ── Summary ─────────────────────────────────────────────────────
echo "=============================================="
echo "  Results Summary"
echo "=============================================="
echo ""
printf "$RESULT_LINES"
echo ""
echo "  Passed: $((TOTAL - FAILED))/$TOTAL"
echo "  Output: $OUTPUT_ROOT/"
echo ""

exit $FAILED
