#!/usr/bin/env bash
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
BUILD_BEFORE_RUN="${HPCC_BUILD:-0}"
AUTO_BUILD_MISSING="${HPCC_AUTO_BUILD:-1}"
BUILD_ONLY=0
BUILD_ALL=0
RECONFIGURE=0
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

if [ ! -f "$BINARY" ] && [ -z "$BINARY_OVERRIDE" ] && [ "$AUTO_BUILD_MISSING" = "1" ] && [ "$BUILD_BEFORE_RUN" -eq 0 ]; then
    echo "Selected $BINARY_PROFILE binary is missing; building it now."
    echo "Use --no-auto-build or HPCC_AUTO_BUILD=0 to disable this behavior."
    echo ""
    build_profile "$BINARY_PROFILE"
    select_binary
fi

if [ ! -f "$BINARY" ]; then
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

shopt -s nullglob

validate_fct_artifacts() {
    local fct_file="$1"
    local flow_file="$2"
    local config_file="$3"
    local report_file="$4"
    local stop_time
    local stop_ns="unknown"

    : > "$report_file"

    if [ ! -f "$fct_file" ]; then
        echo "FAIL: missing FCT file: $fct_file" > "$report_file"
        return 1
    fi

    stop_time="$(awk -F: '/^simulator_stop_time:/ {gsub(/^[ \t"]+|[ \t"]+$/, "", $2); print $2; exit}' "$config_file")"
    if [ -n "$stop_time" ]; then
        stop_ns="$(awk -v s="$stop_time" 'BEGIN {printf "%.0f", s * 1000000000}')"
    fi

    awk -v flow_file="$flow_file" -v stop_ns="$stop_ns" '
        function node_ip(id) {
            return sprintf("%08x", 184549377 + int(id / 256) * 65536 + (id % 256) * 256)
        }
        function is_uint(value) {
            return value ~ /^[0-9]+$/
        }
        function fail(message) {
            print "FAIL: " message
            errors++
        }
        BEGIN {
            expected_total = "unknown"
            if (flow_file != "" && flow_file != "unknown") {
                if ((getline expected_total < flow_file) <= 0) {
                    fail("cannot read flow file " flow_file)
                } else {
                    flow_line = 1
                    while ((getline line < flow_file) > 0) {
                        flow_line++
                        sub(/\r$/, "", line)
                        if (line ~ /^[[:space:]]*$/ || line ~ /^[[:space:]]*#/) {
                            continue
                        }
                        n = split(line, field, /[[:space:]]+/)
                        if (n != 6) {
                            fail("flow line " flow_line " has " n " columns, expected 6")
                            continue
                        }

                        src = field[1]
                        dst = field[2]
                        dport = field[4]
                        size = field[5]
                        start_ns = sprintf("%.0f", field[6] * 1000000000)
                        pair = src SUBSEP dst
                        if (!(pair in next_sport)) {
                            next_sport[pair] = 10000
                        }
                        sport = next_sport[pair]++
                        key = node_ip(src) "|" node_ip(dst) "|" sport "|" dport "|" size "|" start_ns
                        expected[key]++
                        expected_rows++
                    }
                    close(flow_file)
                    if (expected_total != expected_rows) {
                        fail("flow header says " expected_total " row(s), parsed " expected_rows)
                    }
                }
            }
        }
        {
            row++
            if (NF != 8) {
                fail("fct row " row " has " NF " columns, expected 8")
                next
            }
            if ($1 !~ /^[0-9a-fA-F]+$/ || $2 !~ /^[0-9a-fA-F]+$/) {
                fail("fct row " row " has invalid source/destination IP hex")
            }
            if (!is_uint($3) || !is_uint($4) || !is_uint($5) || !is_uint($6) || !is_uint($7) || !is_uint($8)) {
                fail("fct row " row " has non-integer numeric fields")
            }
            if ($5 <= 0) {
                fail("fct row " row " has non-positive size_bytes")
            }
            if ($7 <= 0) {
                fail("fct row " row " has non-positive fct_ns")
            }
            if ($8 <= 0) {
                fail("fct row " row " has non-positive standalone_fct_ns")
            }
            if (stop_ns != "unknown" && $6 + $7 > stop_ns) {
                fail("fct row " row " completes after simulator_stop_time_ns=" stop_ns)
            }

            key = tolower($1) "|" tolower($2) "|" $3 "|" $4 "|" $5 "|" $6
            actual[key]++
        }
        END {
            if (row == 0) {
                fail("fct file is empty")
            }
            if (expected_total != "unknown" && row != expected_total) {
                fail("fct row count " row " != expected flow count " expected_total)
            }
            if (expected_total != "unknown") {
                for (key in expected) {
                    if (actual[key] != expected[key]) {
                        fail("missing/mismatched expected flow " key " expected=" expected[key] " actual=" (key in actual ? actual[key] : 0))
                    }
                }
                for (key in actual) {
                    if (expected[key] != actual[key]) {
                        fail("unexpected completed flow " key " actual=" actual[key] " expected=" (key in expected ? expected[key] : 0))
                    }
                }
            }

            if (errors == 0) {
                print "OK: FCT schema/range checks passed for " row " row(s)."
                if (expected_total != "unknown") {
                    print "OK: FCT flow identity coverage matched " expected_rows " expected flow(s)."
                }
                if (stop_ns != "unknown") {
                    print "OK: all FCT completions fit within simulator_stop_time_ns=" stop_ns "."
                }
            }
            exit errors ? 1 : 0
        }
    ' "$fct_file" > "$report_file"
}

validate_pfc_artifacts() {
    local pfc_file="$1"
    local simulation_log="$2"
    local report_file="$3"
    local pfc_result=0
    local final_paused

    if [ ! -f "$pfc_file" ]; then
        echo "FAIL: missing PFC file: $pfc_file" >> "$report_file"
        return 1
    fi

    set +e
    awk '
        function is_uint(value) {
            return value ~ /^[0-9]+$/
        }
        function fail(message) {
            print "FAIL: " message
            errors++
        }
        NF == 0 { next }
        {
            row++
            if (NF != 6) {
                fail("pfc row " row " has " NF " columns, expected 6: time_ns node_id node_type if_index qIndex type")
                next
            }
            for (i = 1; i <= 6; i++) {
                if (!is_uint($i)) {
                    fail("pfc row " row " has non-integer field " i)
                }
            }
            if ($6 != 0 && $6 != 1) {
                fail("pfc row " row " has invalid type " $6 " expected 0 resume or 1 pause")
            }
            key = $2 "|" $3 "|" $4 "|" $5
            if ($6 == 1) {
                balance[key]++
                pause_count++
            } else {
                balance[key]--
                resume_count++
                if (balance[key] < 0) {
                    fail("pfc row " row " resumes before pause for key " key)
                }
            }
        }
        END {
            for (key in balance) {
                if (balance[key] != 0) {
                    fail("unbalanced PFC key " key " net_pause_count=" balance[key])
                }
            }
            if (errors == 0) {
                print "OK: PFC schema checks passed for " row + 0 " event(s)."
                print "OK: PFC per-queue pause/resume balance passed: pauses=" pause_count + 0 " resumes=" resume_count + 0 "."
            }
            exit errors ? 1 : 0
        }
    ' "$pfc_file" >> "$report_file"
    pfc_result=$?
    set -e

    final_paused="$(awk '
        /HPCC status/ { line = $0 }
        END {
            if (line == "") exit 2
            n = split(line, a, "paused_q=")
            if (n < 2) exit 3
            split(a[2], b, " ")
            print b[1]
        }
    ' "$simulation_log" 2>/dev/null || true)"

    if [ -z "$final_paused" ]; then
        echo "FAIL: could not read final paused_q from simulation.log" >> "$report_file"
        return 1
    fi
    if [ "$final_paused" != "0" ]; then
        echo "FAIL: final status has paused_q=${final_paused}, expected 0" >> "$report_file"
        return 1
    fi

    echo "OK: final status has paused_q=0." >> "$report_file"
    return "$pfc_result"
}

validate_bottleneck_artifacts() {
    local bottleneck_file="$1"
    local pfc_count="$2"
    local report_file="$3"

    if [ ! -f "$bottleneck_file" ]; then
        echo "FAIL: missing bottleneck summary file: $bottleneck_file" >> "$report_file"
        return 1
    fi

    awk -v pfc_count="$pfc_count" '
        function fail(message) {
            print "FAIL: " message
            errors++
        }
        $1 == "max_overall" {
            found = 1
            sw = $2
            port = $3
            pg = $4
            max_egress = $5
            kmin = $6
            kmax = $7
            ratio = $8
            max_shared = $9
            max_ingress = $10
            min_pfc_threshold = $12
            ecn_seen = $13
            pause_seen = $14
            samples = $15
        }
        END {
            if (!found) {
                fail("bottleneck summary has no max_overall row")
            } else {
                if (samples <= 0) fail("bottleneck summary has no samples")
                if (max_egress <= 0 && max_ingress <= 0) fail("bottleneck summary never observed queued bytes")
                if (pfc_count > 0 && ecn_seen != 1 && pause_seen != 1) {
                    fail("PFC events occurred but bottleneck summary saw neither ECN nor pause pressure")
                }
            }
            if (errors == 0) {
                print "OK: bottleneck summary max sw=" sw " port=" port " pg=" pg \
                      " max_egress=" max_egress "B ratio=" ratio \
                      " max_shared=" max_shared "B min_pfc_thr=" min_pfc_threshold "."
            }
            exit errors ? 1 : 0
        }
    ' "$bottleneck_file" >> "$report_file"
}

validate_qlen_artifacts() {
    local qlen_file="$1"
    local report_file="$2"

    if [ ! -f "$qlen_file" ]; then
        echo "FAIL: missing qlen monitor file: $qlen_file" >> "$report_file"
        return 1
    fi

    awk '
        function fail(message) {
            print "FAIL: " message
            errors++
        }
        /^time:/ {
            dump_count++
            next
        }
        NF >= 3 {
            port_rows++
            for (i = 3; i <= NF; i++) {
                sample_bins += $i
            }
        }
        END {
            if (dump_count < 2) fail("qlen monitor has only " dump_count " dump(s), expected at least 2")
            if (port_rows == 0) fail("qlen monitor has no switch-port rows")
            if (sample_bins == 0) fail("qlen monitor has zero recorded samples")
            if (errors == 0) {
                print "OK: qlen monitor resolution check passed: dumps=" dump_count \
                      " port_rows=" port_rows " sample_bins=" sample_bins "."
            }
            exit errors ? 1 : 0
        }
    ' "$qlen_file" >> "$report_file"
}

validate_trace_artifacts() {
    local trace_file="$1"
    local enable_trace="$2"
    local report_file="$3"

    if [ "$enable_trace" != "1" ]; then
        echo "OK: trace sanity skipped because enable_trace=${enable_trace}." >> "$report_file"
        return 0
    fi

    if [ ! -f "$trace_file" ]; then
        echo "FAIL: missing trace file: $trace_file" >> "$report_file"
        return 1
    fi

    python3 - "$trace_file" >> "$report_file" <<'PY'
import os
import struct
import sys

path = sys.argv[1]
size = os.path.getsize(path)

def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)

if size == 0:
    fail(f"trace file is empty: {path}")

with open(path, "rb") as f:
    raw = f.read(4)
    if len(raw) != 4:
        fail("trace file is too small to contain SimSetting header")
    (port_count,) = struct.unpack("<I", raw)
    if port_count == 0 or port_count > 100000:
        fail(f"invalid SimSetting port_count={port_count}")

    header_size = 4 + port_count * (2 + 1 + 8) + 4
    if size <= header_size:
        fail(f"trace file has no TraceFormat records after header_size={header_size}")

    f.seek(header_size)
    remaining = size - header_size
    record_size = 56
    if remaining % record_size != 0:
        fail(f"trace payload size {remaining} is not a multiple of TraceFormat size {record_size}")

    records = remaining // record_size
    event_counts = [0, 0, 0, 0]
    invalid_events = 0
    data_packets = 0
    ack_nack_packets = 0
    pfc_packets = 0
    cnp_packets = 0
    switch_records = 0
    host_records = 0

    for _ in range(records):
        rec = f.read(record_size)
        event = rec[27]
        l3prot = rec[26]
        node_type = rec[29]

        if event < 4:
            event_counts[event] += 1
        else:
            invalid_events += 1

        if l3prot == 0x11:
            data_packets += 1
        elif l3prot in (0xFC, 0xFD):
            ack_nack_packets += 1
        elif l3prot == 0xFE:
            pfc_packets += 1
        elif l3prot == 0xFF:
            cnp_packets += 1

        if node_type == 1:
            switch_records += 1
        elif node_type == 0:
            host_records += 1

if invalid_events:
    fail(f"trace has {invalid_events} invalid event code(s)")
if records == 0:
    fail("trace has zero records")
if event_counts[0] == 0 or event_counts[1] == 0 or event_counts[2] == 0:
    fail(f"trace missing required event class: recv={event_counts[0]} enqu={event_counts[1]} dequ={event_counts[2]}")
if data_packets == 0:
    fail("trace has no RDMA data packet records")
if ack_nack_packets == 0:
    fail("trace has no ACK/NACK packet records")
if switch_records == 0:
    fail("trace has no switch-side records")
if host_records == 0:
    fail("trace has no host-side records")

print(
    "OK: trace sanity passed: "
    f"records={records} recv={event_counts[0]} enqu={event_counts[1]} "
    f"dequ={event_counts[2]} drop={event_counts[3]} data={data_packets} "
    f"ack_nack={ack_nack_packets} pfc={pfc_packets} cnp={cnp_packets} "
    f"host_records={host_records} switch_records={switch_records}."
)
PY
}

if [ "$#" -gt 0 ]; then
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

echo "=============================================="
echo "  HPCC Algorithm Validation Mini Runs"
echo "=============================================="
echo ""
echo "  Binary:  $BINARY"
echo "  Profile: $BINARY_PROFILE"
echo "  Configs: $TOTAL file(s)"
echo ""

CURRENT=0
FAILED=0
RESULT_LINES=""

for config in "${CONFIGS[@]}"; do
    CURRENT=$((CURRENT + 1))
    if [ ! -f "$config" ]; then
        echo "ERROR: Config not found: $config"
        FAILED=$((FAILED + 1))
        continue
    fi

    NAME="$(basename "$config" .yml)"
    RUN_OUTPUT="$OUTPUT_ROOT/$NAME"
    mkdir -p "$RUN_OUTPUT"
    cp "$config" "$RUN_OUTPUT/config.yml"

    CFG_FLOW="$(awk -F: '/^flow_file:/ {gsub(/^[ \t"]+|[ \t"]+$/, "", $2); print $2; exit}' "$config")"
    CFG_TRACE_OUTPUT="$(awk -F: '/^trace_output_file:/ {gsub(/^[ \t"]+|[ \t"]+$/, "", $2); print $2; exit}' "$config")"
    CFG_ENABLE_TRACE="$(awk -F: '/^enable_trace:/ {gsub(/^[ \t"]+|[ \t"]+$/, "", $2); print $2; exit}' "$config")"
    EXPECTED_FLOWS="unknown"
    FLOW_PATH="unknown"
    TRACE_PATH="unknown"
    if [ -n "$CFG_FLOW" ] && [ -f "$HPCC_DIR/$CFG_FLOW" ]; then
        FLOW_PATH="$HPCC_DIR/$CFG_FLOW"
        EXPECTED_FLOWS="$(head -1 "$HPCC_DIR/$CFG_FLOW" | tr -d '[:space:]')"
    fi
    if [ -n "$CFG_TRACE_OUTPUT" ]; then
        if [ "${CFG_TRACE_OUTPUT:0:1}" = "/" ]; then
            TRACE_PATH="$CFG_TRACE_OUTPUT"
        else
            TRACE_PATH="$HPCC_DIR/$CFG_TRACE_OUTPUT"
        fi
    fi
    if [ -z "$CFG_ENABLE_TRACE" ]; then
        CFG_ENABLE_TRACE="0"
    fi

    echo "----------------------------------------------"
    echo "[$CURRENT/$TOTAL] $NAME"
    echo "----------------------------------------------"
    echo "  Config: $config"
    echo "  Output: $RUN_OUTPUT/"
    echo "  Flows:  $EXPECTED_FLOWS expected"
    echo ""

    cd "$HPCC_DIR"
    START_TIME=$(date +%s)
    set +e
    "$BINARY" "$config" 2>&1 | tee "$RUN_OUTPUT/simulation.log"
    SIM_EXIT=${PIPESTATUS[0]}
    set -e
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    echo ""

    FCT_FILE="$RUN_OUTPUT/fct.txt"
    PFC_FILE="$RUN_OUTPUT/pfc.txt"
    QLEN_FILE="$RUN_OUTPUT/qlen.txt"
    BOTTLENECK_FILE="$RUN_OUTPUT/bottleneck.txt"
    VALIDATION_REPORT="$RUN_OUTPUT/validation_checks.txt"
    FLOW_COUNT=0
    PFC_COUNT=0
    FCT_CHECK_EXIT=1
    PFC_CHECK_EXIT=1
    BOTTLENECK_CHECK_EXIT=1
    QLEN_CHECK_EXIT=1
    TRACE_CHECK_EXIT=1
    if [ -f "$FCT_FILE" ]; then
        FLOW_COUNT=$(wc -l < "$FCT_FILE" | tr -d ' ')
    fi
    if [ -f "$PFC_FILE" ]; then
        PFC_COUNT=$(wc -l < "$PFC_FILE" | tr -d ' ')
    fi

    set +e
    validate_fct_artifacts "$FCT_FILE" "$FLOW_PATH" "$config" "$VALIDATION_REPORT"
    FCT_CHECK_EXIT=$?
    validate_pfc_artifacts "$PFC_FILE" "$RUN_OUTPUT/simulation.log" "$VALIDATION_REPORT"
    PFC_CHECK_EXIT=$?
    validate_bottleneck_artifacts "$BOTTLENECK_FILE" "$PFC_COUNT" "$VALIDATION_REPORT"
    BOTTLENECK_CHECK_EXIT=$?
    validate_qlen_artifacts "$QLEN_FILE" "$VALIDATION_REPORT"
    QLEN_CHECK_EXIT=$?
    validate_trace_artifacts "$TRACE_PATH" "$CFG_ENABLE_TRACE" "$VALIDATION_REPORT"
    TRACE_CHECK_EXIT=$?
    set -e

    if [ -f "$VALIDATION_REPORT" ]; then
        sed 's/^/  /' "$VALIDATION_REPORT"
    fi

    if [ "$SIM_EXIT" -eq 0 ] && { [ "$EXPECTED_FLOWS" = "unknown" ] || [ "$FLOW_COUNT" = "$EXPECTED_FLOWS" ]; } \
        && [ "$FCT_CHECK_EXIT" -eq 0 ] && [ "$PFC_CHECK_EXIT" -eq 0 ] \
        && [ "$BOTTLENECK_CHECK_EXIT" -eq 0 ] && [ "$QLEN_CHECK_EXIT" -eq 0 ] \
        && [ "$TRACE_CHECK_EXIT" -eq 0 ]; then
        echo "  Result: OK (exit=0, ${ELAPSED}s, ${FLOW_COUNT}/${EXPECTED_FLOWS} flows, ${PFC_COUNT} pfc events, validation checks ok)"
        RESULT_LINES="${RESULT_LINES}  OK   ${NAME}  ${ELAPSED}s  ${FLOW_COUNT}/${EXPECTED_FLOWS} flows  ${PFC_COUNT} pfc  checks=ok\n"
    elif [ "$SIM_EXIT" -eq 0 ]; then
        echo "  Result: FAILED (exit=0, ${ELAPSED}s, completed ${FLOW_COUNT}/${EXPECTED_FLOWS} flows, fct=${FCT_CHECK_EXIT}, pfc=${PFC_CHECK_EXIT}, bottleneck=${BOTTLENECK_CHECK_EXIT}, qlen=${QLEN_CHECK_EXIT}, trace=${TRACE_CHECK_EXIT})"
        RESULT_LINES="${RESULT_LINES}  FAIL ${NAME}  incomplete=${FLOW_COUNT}/${EXPECTED_FLOWS} fct=${FCT_CHECK_EXIT} pfc=${PFC_CHECK_EXIT} bottleneck=${BOTTLENECK_CHECK_EXIT} qlen=${QLEN_CHECK_EXIT} trace=${TRACE_CHECK_EXIT}\n"
        FAILED=$((FAILED + 1))
    else
        echo "  Result: FAILED (exit=$SIM_EXIT, ${ELAPSED}s)"
        RESULT_LINES="${RESULT_LINES}  FAIL ${NAME}  exit=$SIM_EXIT\n"
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

echo "=============================================="
echo "  Results Summary"
echo "=============================================="
echo ""
printf "%b" "$RESULT_LINES"
echo ""
echo "  Passed: $((TOTAL - FAILED))/$TOTAL"
echo "  Output: $OUTPUT_ROOT/"
echo ""

exit "$FAILED"
