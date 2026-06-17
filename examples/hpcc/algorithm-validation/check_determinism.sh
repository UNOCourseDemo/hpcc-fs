#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_ROOT="$SCRIPT_DIR/output"

usage() {
    cat <<EOF
Usage: $0 [--debug|--release|--optimized] [--build] [--build-only|--build-all] [--reconfigure] [--no-auto-build] [--binary PATH] <config.yml | configs/name.yml>

Run/build options are forwarded to run.sh. If --build-only or --build-all is
used, this script builds through run.sh and exits without running determinism.
EOF
}

RUN_ARGS=()
CONFIG_ARG=""
BUILD_CONTROL_ONLY=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --debug|--release|--optimized|--build|--reconfigure|--no-auto-build)
            RUN_ARGS+=("$1")
            ;;
        --build-only|--build-all)
            RUN_ARGS+=("$1")
            BUILD_CONTROL_ONLY=1
            ;;
        --binary)
            RUN_ARGS+=("$1")
            shift
            if [ "$#" -eq 0 ]; then
                echo "ERROR: --binary requires a path"
                exit 2
            fi
            RUN_ARGS+=("$1")
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            echo "ERROR: Unknown option: $1"
            usage
            exit 2
            ;;
        *)
            if [ -n "$CONFIG_ARG" ]; then
                echo "ERROR: Multiple configs are not supported for determinism"
                usage
                exit 2
            fi
            CONFIG_ARG="$1"
            ;;
    esac
    shift
done

if [ "$BUILD_CONTROL_ONLY" -eq 1 ]; then
    exec bash "$SCRIPT_DIR/run.sh" "${RUN_ARGS[@]}"
fi

if [ -z "$CONFIG_ARG" ]; then
    usage
    exit 1
fi

if [ "${CONFIG_ARG:0:1}" = "/" ]; then
    CONFIG_PATH="$CONFIG_ARG"
else
    CONFIG_PATH="$SCRIPT_DIR/$CONFIG_ARG"
fi

if [ ! -f "$CONFIG_PATH" ]; then
    echo "ERROR: Config not found: $CONFIG_PATH"
    exit 1
fi

NAME="$(basename "$CONFIG_PATH" .yml)"
DET_ROOT="$OUTPUT_ROOT/${NAME}_determinism_$(date +%Y%m%d%H%M%S)"
mkdir -p "$DET_ROOT/run1" "$DET_ROOT/run2"

copy_artifacts() {
    local src="$1"
    local dst="$2"
    shift 2
    for artifact in "$@"; do
        if [ ! -f "$src/$artifact" ]; then
            echo "ERROR: Missing artifact for determinism: $src/$artifact"
            exit 1
        fi
        cp "$src/$artifact" "$dst/$artifact"
    done
}

ARTIFACTS=(fct.txt pfc.txt bottleneck.txt qlen.txt validation_checks.txt)

echo "=============================================="
echo "  HPCC Determinism Check"
echo "=============================================="
echo ""
echo "  Config: $CONFIG_PATH"
echo "  Output: $DET_ROOT/"
if [ "${#RUN_ARGS[@]}" -gt 0 ]; then
    echo "  Run opts: ${RUN_ARGS[*]}"
fi
echo ""

echo "---- run 1 ----"
bash "$SCRIPT_DIR/run.sh" "${RUN_ARGS[@]+"${RUN_ARGS[@]}"}" "$CONFIG_ARG"
copy_artifacts "$OUTPUT_ROOT/$NAME" "$DET_ROOT/run1" "${ARTIFACTS[@]}"

echo "---- run 2 ----"
bash "$SCRIPT_DIR/run.sh" "${RUN_ARGS[@]+"${RUN_ARGS[@]}"}" "$CONFIG_ARG"
copy_artifacts "$OUTPUT_ROOT/$NAME" "$DET_ROOT/run2" "${ARTIFACTS[@]}"

FAILED=0
REPORT="$DET_ROOT/determinism_report.txt"
: > "$REPORT"

for artifact in "${ARTIFACTS[@]}"; do
    if cmp -s "$DET_ROOT/run1/$artifact" "$DET_ROOT/run2/$artifact"; then
        HASH="$(shasum -a 256 "$DET_ROOT/run1/$artifact" | awk '{print $1}')"
        echo "OK: $artifact hash=$HASH" | tee -a "$REPORT"
    else
        echo "FAIL: $artifact differs between repeated runs" | tee -a "$REPORT"
        FAILED=1
    fi
done

if [ "$FAILED" -eq 0 ]; then
    echo "Result: OK, deterministic artifacts matched." | tee -a "$REPORT"
else
    echo "Result: FAILED, deterministic artifact mismatch." | tee -a "$REPORT"
fi

echo ""
echo "Report: $REPORT"
exit "$FAILED"
