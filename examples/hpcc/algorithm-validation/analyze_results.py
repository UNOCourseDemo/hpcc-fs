#!/usr/bin/env python3
"""Summarize HPCC algorithm-validation output artifacts.

The script is intentionally dependency-free so it can run inside the project
venv without installing analysis packages.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
HPCC_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_ROOT = SCRIPT_DIR / "output"
TRACE_RECORD_SIZE = 56
KNOWN_ORDER = {
    "hpcc_smoke": 0,
    "hpcc_incast": 1,
    "hpcc_pint_incast": 2,
    "dcqcn_incast": 3,
    "dctcp_incast": 4,
    "timely_incast": 5,
    "hpcc_mixed": 6,
}


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * pct / 100.0
    lo = math.floor(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def fmt_float(value: Any, digits: int = 3, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}{suffix}"
    return f"{value}{suffix}"


def read_lines(path: Path, warnings: list[str]) -> list[str]:
    if not path.exists():
        warnings.append(f"missing {path.name}")
        return []
    return path.read_text(errors="replace").splitlines()


def parse_config_values(path: Path, warnings: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        warnings.append("missing config.yml")
        return values
    wanted = {
        "flow_file",
        "fct_output_file",
        "pfc_output_file",
        "bottleneck_output_file",
        "qlen_mon_file",
        "trace_output_file",
    }
    for line in path.read_text(errors="replace").splitlines():
        if ":" not in line or line[:1].isspace():
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in wanted:
            values[key] = value.strip().strip('"').strip("'")
    return values


def resolve_hpcc_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else HPCC_DIR / path


def parse_flow_input(path: Path | None, warnings: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "exists": False,
        "ok": False,
        "expected_count": None,
        "data_rows": 0,
        "path": str(path) if path else None,
    }
    if path is None:
        warnings.append("config.yml has no flow_file")
        return result
    if not path.exists():
        warnings.append(f"missing flow input {path}")
        return result

    result["exists"] = True
    local_errors = 0
    previous_start: float | None = None
    with path.open(errors="replace") as stream:
        header = stream.readline()
        try:
            header_parts = header.split()
            if len(header_parts) != 1:
                raise ValueError
            expected = int(header_parts[0])
            if expected < 0:
                raise ValueError
            result["expected_count"] = expected
        except ValueError:
            warnings.append(f"{path.name}: header must be one non-negative integer")
            local_errors += 1
            expected = None

        for line_no, line in enumerate(stream, 2):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            result["data_rows"] += 1
            if len(parts) != 6:
                if local_errors < 5:
                    warnings.append(f"{path.name}:{line_no} has {len(parts)} flow columns, expected 6")
                local_errors += 1
                continue
            try:
                src = int(parts[0])
                dst = int(parts[1])
                pg = int(parts[2])
                _dport = int(parts[3])
                size = int(parts[4])
                start = float(parts[5])
            except ValueError:
                if local_errors < 5:
                    warnings.append(f"{path.name}:{line_no} has invalid flow fields")
                local_errors += 1
                continue
            if src == dst or pg < 0 or pg >= 8 or size <= 0 or start < 0:
                if local_errors < 5:
                    warnings.append(f"{path.name}:{line_no} has invalid flow values")
                local_errors += 1
            if previous_start is not None and start + 1e-12 < previous_start:
                if local_errors < 5:
                    warnings.append(f"{path.name}:{line_no} is not sorted by start time")
                local_errors += 1
            previous_start = start

    if expected is not None and result["data_rows"] != expected:
        warnings.append(
            f"{path.name}: header says {expected} flow(s), parsed {result['data_rows']} data row(s)"
        )
        local_errors += 1
    result["ok"] = local_errors == 0
    return result


def parse_fct(path: Path, warnings: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(read_lines(path, warnings), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 8:
            warnings.append(f"{path.name}:{line_no} has {len(parts)} columns, expected 8")
            continue
        try:
            size = int(parts[4])
            start_ns = int(parts[5])
            fct_ns = int(parts[6])
            standalone_ns = int(parts[7])
        except ValueError:
            warnings.append(f"{path.name}:{line_no} has non-integer numeric fields")
            continue
        rows.append(
            {
                "sip": parts[0].lower(),
                "dip": parts[1].lower(),
                "sport": int(parts[2]),
                "dport": int(parts[3]),
                "size_bytes": size,
                "start_ns": start_ns,
                "fct_ns": fct_ns,
                "standalone_fct_ns": standalone_ns,
                "fct_ms": fct_ns / 1_000_000.0,
                "standalone_ms": standalone_ns / 1_000_000.0,
                "slowdown": fct_ns / standalone_ns if standalone_ns else None,
            }
        )
    return rows


def size_bucket(size: int) -> str:
    if size < 1_024:
        return "<1KB"
    if size < 10 * 1_024:
        return "1-10KB"
    if size < 100 * 1_024:
        return "10-100KB"
    if size < 1_000 * 1_024:
        return "100KB-1MB"
    if size < 10_000 * 1_024:
        return "1-10MB"
    return ">=10MB"


def summarize_fct_group(label: Any, group: list[dict[str, Any]]) -> dict[str, Any]:
    group_fct = [row["fct_ms"] for row in group]
    group_slowdown = [row["slowdown"] for row in group if row["slowdown"] is not None]
    return {
        "size_bytes": label,
        "flows": len(group),
        "min_fct_ms": min(group_fct) if group_fct else None,
        "median_fct_ms": percentile(group_fct, 50),
        "p90_fct_ms": percentile(group_fct, 90),
        "p99_fct_ms": percentile(group_fct, 99),
        "max_fct_ms": max(group_fct) if group_fct else None,
        "median_slowdown": percentile(group_slowdown, 50),
        "p99_slowdown": percentile(group_slowdown, 99),
        "max_slowdown": max(group_slowdown) if group_slowdown else None,
    }


def summarize_fct(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fct_ms = [row["fct_ms"] for row in rows]
    slowdowns = [row["slowdown"] for row in rows if row["slowdown"] is not None]
    by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_size[row["size_bytes"]].append(row)
        by_bucket[size_bucket(row["size_bytes"])].append(row)

    size_rows = []
    for size, group in sorted(by_size.items()):
        size_rows.append(summarize_fct_group(size, group))

    bucket_order = {
        "<1KB": 0,
        "1-10KB": 1,
        "10-100KB": 2,
        "100KB-1MB": 3,
        "1-10MB": 4,
        ">=10MB": 5,
    }
    bucket_rows = [
        summarize_fct_group(label, group)
        for label, group in sorted(by_bucket.items(), key=lambda item: bucket_order[item[0]])
    ]

    return {
        "flows": len(rows),
        "mean_fct_ms": mean(fct_ms),
        "median_fct_ms": percentile(fct_ms, 50),
        "p90_fct_ms": percentile(fct_ms, 90),
        "p99_fct_ms": percentile(fct_ms, 99),
        "max_fct_ms": max(fct_ms) if fct_ms else None,
        "mean_slowdown": mean(slowdowns),
        "p90_slowdown": percentile(slowdowns, 90),
        "max_slowdown": max(slowdowns) if slowdowns else None,
        "by_size": size_rows,
        "by_size_bucket": bucket_rows,
    }


def parse_pfc(path: Path, warnings: list[str]) -> list[tuple[int, int, int, int, int, int]]:
    rows = []
    for line_no, line in enumerate(read_lines(path, warnings), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 6:
            warnings.append(f"{path.name}:{line_no} has {len(parts)} columns, expected 6")
            continue
        try:
            row = tuple(int(part) for part in parts)
        except ValueError:
            warnings.append(f"{path.name}:{line_no} has non-integer fields")
            continue
        if row[5] not in (0, 1):
            warnings.append(f"{path.name}:{line_no} has invalid type {row[5]}")
        rows.append(row)
    return rows


def summarize_pfc(rows: list[tuple[int, int, int, int, int, int]]) -> dict[str, Any]:
    pauses = sum(1 for row in rows if row[5] == 1)
    resumes = sum(1 for row in rows if row[5] == 0)
    queues = {(row[1], row[2], row[3], row[4]) for row in rows}
    event_counter: Counter[tuple[int, int, int, int, int]] = Counter()
    top_queues = []
    collapsed: Counter[tuple[int, int, int, int]] = Counter()
    for _time_ns, node, node_type, if_index, q_index, event_type in rows:
        collapsed[(node, node_type, if_index, q_index)] += 1
        event_counter[(node, node_type, if_index, q_index, event_type)] += 1
    for (node, node_type, if_index, q_index), count in collapsed.most_common(8):
        pause_count = event_counter[(node, node_type, if_index, q_index, 1)]
        resume_count = event_counter[(node, node_type, if_index, q_index, 0)]
        top_queues.append(
            {
                "node_id": node,
                "node_type": node_type,
                "if_index": if_index,
                "q_index": q_index,
                "events": count,
                "pauses": pause_count,
                "resumes": resume_count,
            }
        )
    times = [row[0] for row in rows]
    return {
        "events": len(rows),
        "pauses": pauses,
        "resumes": resumes,
        "balanced": pauses == resumes,
        "unique_queues": len(queues),
        "first_event_ms": min(times) / 1_000_000.0 if times else None,
        "last_event_ms": max(times) / 1_000_000.0 if times else None,
        "top_queues": top_queues,
    }


def parse_bottleneck(path: Path, warnings: list[str]) -> dict[str, Any]:
    rows = []
    max_overall = None
    for line_no, line in enumerate(read_lines(path, warnings), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        is_max = parts[0] == "max_overall"
        offset = 1 if is_max else 0
        if len(parts) - offset != 14:
            warnings.append(f"{path.name}:{line_no} has unexpected bottleneck columns")
            continue
        try:
            row = {
                "sw": int(parts[offset + 0]),
                "port": int(parts[offset + 1]),
                "pg": int(parts[offset + 2]),
                "max_egress_bytes": int(parts[offset + 3]),
                "kmin": int(parts[offset + 4]),
                "kmax": int(parts[offset + 5]),
                "max_ratio": float(parts[offset + 6]),
                "max_shared_bytes": int(parts[offset + 7]),
                "max_ingress_bytes": int(parts[offset + 8]),
                "max_hdrm_bytes": int(parts[offset + 9]),
                "min_pfc_threshold": int(parts[offset + 10]),
                "ecn_seen": bool(int(parts[offset + 11])),
                "pause_seen": bool(int(parts[offset + 12])),
                "samples": int(parts[offset + 13]),
            }
        except ValueError:
            warnings.append(f"{path.name}:{line_no} has invalid bottleneck values")
            continue
        if is_max:
            max_overall = row
        else:
            rows.append(row)

    active_rows = [
        row
        for row in rows
        if row["max_egress_bytes"]
        or row["max_shared_bytes"]
        or row["max_ingress_bytes"]
        or row["max_hdrm_bytes"]
        or row["ecn_seen"]
        or row["pause_seen"]
    ]
    return {
        "max_overall": max_overall,
        "active_rows": active_rows,
        "ecn_rows": sum(1 for row in rows if row["ecn_seen"]),
        "pause_rows": sum(1 for row in rows if row["pause_seen"]),
    }


def q_from_counts(counts: list[int], pct: float) -> int:
    total = sum(counts)
    if total == 0:
        return 0
    target = total * pct / 100.0
    seen = 0
    for index, count in enumerate(counts):
        seen += count
        if seen >= target:
            return index
    return len(counts) - 1


def parse_qlen(path: Path, warnings: list[str]) -> dict[str, Any]:
    blocks: list[tuple[int, list[dict[str, Any]]]] = []
    current_time: int | None = None
    current_rows: list[dict[str, Any]] = []

    for line_no, line in enumerate(read_lines(path, warnings), 1):
        if not line.strip():
            continue
        if line.startswith("time:"):
            if current_time is not None:
                blocks.append((current_time, current_rows))
            try:
                current_time = int(line.split()[1])
            except (IndexError, ValueError):
                warnings.append(f"{path.name}:{line_no} has invalid time marker")
                current_time = 0
            current_rows = []
            continue

        parts = line.split()
        if len(parts) < 3:
            warnings.append(f"{path.name}:{line_no} has too few qlen columns")
            continue
        try:
            sw = int(parts[0])
            port = int(parts[1])
            counts = [int(part) for part in parts[2:]]
        except ValueError:
            warnings.append(f"{path.name}:{line_no} has invalid qlen values")
            continue
        samples = sum(counts)
        max_kb = max((index for index, count in enumerate(counts) if count), default=0)
        mean_kb = (
            sum(index * count for index, count in enumerate(counts)) / samples
            if samples
            else None
        )
        current_rows.append(
            {
                "sw": sw,
                "port": port,
                "samples": samples,
                "mean_kb": mean_kb,
                "p95_kb": q_from_counts(counts, 95),
                "p99_kb": q_from_counts(counts, 99),
                "max_kb": max_kb,
            }
        )

    if current_time is not None:
        blocks.append((current_time, current_rows))

    final_time, final_rows = blocks[-1] if blocks else (None, [])
    max_row = max(final_rows, key=lambda row: row["max_kb"], default=None)
    return {
        "dumps": len(blocks),
        "final_time_ns": final_time,
        "port_rows": len(final_rows),
        "max_port": max_row,
    }


def parse_final_status(path: Path, warnings: list[str]) -> dict[str, Any]:
    text = "\n".join(read_lines(path, warnings))
    status_lines = [line for line in text.splitlines() if "HPCC status" in line]
    final = status_lines[-1] if status_lines else ""
    status: dict[str, Any] = {"raw": final}

    started = re.search(r"started=(\d+)/(\d+)", final)
    if started:
        status["started"] = int(started.group(1))
        status["total_flows"] = int(started.group(2))

    for key in [
        "completed",
        "pending",
        "active",
        "qps",
        "bytes_left",
        "in_flight",
        "paused_q",
        "ecn_q",
        "events",
    ]:
        match = re.search(rf"{key}=(\d+)", final)
        if match:
            status[key] = int(match.group(1))

    elapsed = re.search(r"Elapsed: ([0-9.]+)s", text)
    if elapsed:
        status["elapsed_s"] = float(elapsed.group(1))

    status["drained"] = (
        status.get("started") == status.get("total_flows")
        and status.get("completed") == status.get("total_flows")
        and status.get("pending") == 0
        and status.get("active") == 0
        and status.get("qps") == 0
        and status.get("bytes_left") == 0
        and status.get("in_flight") == 0
        and status.get("paused_q") == 0
    )
    return status


def parse_trace(path: Path, warnings: list[str], deep_trace: bool) -> dict[str, Any]:
    if not path.exists():
        warnings.append("missing trace.tr")
        return {"exists": False}

    size = path.stat().st_size
    result: dict[str, Any] = {"exists": True, "size_bytes": size}
    if size < 4:
        warnings.append("trace.tr is too small to contain port count")
        return result

    with path.open("rb") as stream:
        port_count = struct.unpack("<I", stream.read(4))[0]
        result["port_count"] = port_count
        if port_count == 0 or port_count > 100_000:
            warnings.append(f"trace.tr has suspicious port_count={port_count}")
            return result

        header_size = 4 + port_count * (2 + 1 + 8) + 4
        result["header_size_bytes"] = header_size
        if size < header_size:
            warnings.append("trace.tr is smaller than its SimSetting header")
            return result

        payload = size - header_size
        result["payload_bytes"] = payload
        if payload % TRACE_RECORD_SIZE != 0:
            warnings.append("trace.tr payload is not aligned to TraceFormat records")
            result["records"] = None
            return result

        records = payload // TRACE_RECORD_SIZE
        result["records"] = records
        if not deep_trace or records == 0:
            return result

        stream.seek(header_size)
        event_counts = [0, 0, 0, 0]
        invalid_events = 0
        packet_counts = {"data": 0, "ack_nack": 0, "pfc": 0, "cnp": 0}
        node_counts = {"host_records": 0, "switch_records": 0}
        chunk_size = TRACE_RECORD_SIZE * 8192
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            for offset in range(0, len(chunk), TRACE_RECORD_SIZE):
                record = chunk[offset : offset + TRACE_RECORD_SIZE]
                if len(record) != TRACE_RECORD_SIZE:
                    continue
                event = record[27]
                l3prot = record[26]
                node_type = record[29]
                if event < 4:
                    event_counts[event] += 1
                else:
                    invalid_events += 1
                if l3prot == 0x11:
                    packet_counts["data"] += 1
                elif l3prot in (0xFC, 0xFD):
                    packet_counts["ack_nack"] += 1
                elif l3prot == 0xFE:
                    packet_counts["pfc"] += 1
                elif l3prot == 0xFF:
                    packet_counts["cnp"] += 1
                if node_type == 0:
                    node_counts["host_records"] += 1
                elif node_type == 1:
                    node_counts["switch_records"] += 1

        result["deep"] = {
            "recv": event_counts[0],
            "enqu": event_counts[1],
            "dequ": event_counts[2],
            "drop": event_counts[3],
            "invalid_events": invalid_events,
            **packet_counts,
            **node_counts,
        }
    return result


def parse_validation(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "ok": False, "ok_lines": 0, "fail_lines": 0}
    lines = path.read_text(errors="replace").splitlines()
    fail_lines = [line for line in lines if line.startswith("FAIL:")]
    ok_lines = [line for line in lines if line.startswith("OK:")]
    return {
        "exists": True,
        "ok": not fail_lines and bool(ok_lines),
        "ok_lines": len(ok_lines),
        "fail_lines": len(fail_lines),
    }


def analyze_run(path: Path, deep_trace: bool) -> dict[str, Any]:
    warnings: list[str] = []
    config = parse_config_values(path / "config.yml", warnings)
    flow_path = resolve_hpcc_path(config["flow_file"]) if config.get("flow_file") else None
    flow_input = parse_flow_input(flow_path, warnings)
    fct_rows = parse_fct(path / "fct.txt", warnings)
    pfc_rows = parse_pfc(path / "pfc.txt", warnings)
    expected_flows = flow_input.get("expected_count")
    if expected_flows is not None and len(fct_rows) != expected_flows:
        warnings.append(
            f"fct.txt has {len(fct_rows)} row(s), expected {expected_flows} from flow_file"
        )
    result = {
        "name": path.name,
        "path": str(path),
        "warnings": warnings,
        "config": config,
        "flow_input": flow_input,
        "fct": summarize_fct(fct_rows),
        "pfc": summarize_pfc(pfc_rows),
        "bottleneck": parse_bottleneck(path / "bottleneck.txt", warnings),
        "qlen": parse_qlen(path / "qlen.txt", warnings),
        "status": parse_final_status(path / "simulation.log", warnings),
        "trace": parse_trace(path / "trace.tr", warnings, deep_trace),
        "validation": parse_validation(path / "validation_checks.txt"),
    }
    return result


def discover_runs(output_root: Path, names: list[str]) -> list[Path]:
    if names:
        runs = []
        for name in names:
            path = Path(name)
            if not path.is_absolute():
                path = output_root / name
            runs.append(path)
        return runs

    runs = [
        path
        for path in output_root.iterdir()
        if path.is_dir() and (path / "fct.txt").exists()
    ]
    return sorted(runs, key=lambda path: (KNOWN_ORDER.get(path.name, 999), path.name))


def flat_summary(result: dict[str, Any]) -> dict[str, Any]:
    fct = result["fct"]
    pfc = result["pfc"]
    bmax = result["bottleneck"].get("max_overall") or {}
    qmax = result["qlen"].get("max_port") or {}
    status = result["status"]
    trace = result["trace"]
    flow_input = result.get("flow_input", {})
    bottleneck = (
        f"sw{bmax.get('sw')}/p{bmax.get('port')}/pg{bmax.get('pg')}"
        if bmax
        else "n/a"
    )
    qmax_text = (
        f"sw{qmax.get('sw')}/p{qmax.get('port')}"
        if qmax
        else "n/a"
    )
    return {
        "run": result["name"],
        "input_ok": flow_input.get("ok"),
        "input_flows": flow_input.get("expected_count"),
        "flows": fct["flows"],
        "final_drained": status.get("drained"),
        "elapsed_s": status.get("elapsed_s"),
        "mean_fct_ms": fct["mean_fct_ms"],
        "median_fct_ms": fct["median_fct_ms"],
        "p90_fct_ms": fct["p90_fct_ms"],
        "max_fct_ms": fct["max_fct_ms"],
        "mean_slowdown": fct["mean_slowdown"],
        "max_slowdown": fct["max_slowdown"],
        "pfc_events": pfc["events"],
        "pfc_queues": pfc["unique_queues"],
        "bottleneck": bottleneck,
        "bottleneck_max_kb": bmax.get("max_egress_bytes", 0) / 1000.0 if bmax else None,
        "bottleneck_ratio": bmax.get("max_ratio") if bmax else None,
        "qlen_max_port": qmax_text,
        "qlen_max_kb": qmax.get("max_kb") if qmax else None,
        "qlen_p99_kb": qmax.get("p99_kb") if qmax else None,
        "trace_records": trace.get("records"),
        "validation_ok": result["validation"].get("ok"),
        "warnings": len(result.get("warnings", [])),
    }


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_markdown(results: list[dict[str, Any]], explain: bool) -> str:
    lines = ["# HPCC Validation Result Analysis", ""]
    lines.append("Generated from existing HPCC output artifacts.")
    lines.append("")

    rows = []
    for result in results:
        flat = flat_summary(result)
        rows.append(
            [
                flat["run"],
                "yes" if flat["input_ok"] else "no",
                str(flat["input_flows"] if flat["input_flows"] is not None else "n/a"),
                str(flat["flows"]),
                "yes" if flat["final_drained"] else "no",
                fmt_float(flat["mean_fct_ms"]),
                fmt_float(flat["p90_fct_ms"]),
                fmt_float(flat["max_fct_ms"]),
                fmt_float(flat["mean_slowdown"], 1) + "x",
                str(flat["pfc_events"]),
                flat["bottleneck"],
                fmt_float(flat["bottleneck_max_kb"], 1, " KB"),
                fmt_float(flat["bottleneck_ratio"], 2),
                fmt_float(flat["qlen_max_kb"], 0, " KB"),
                str(flat["trace_records"] if flat["trace_records"] is not None else "n/a"),
                str(flat["warnings"]),
            ]
        )
    lines.append("## Run Summary")
    lines.append("")
    lines.append(
        markdown_table(
            [
                "Run",
                "Input OK",
                "Input Flows",
                "Flows",
                "Drained",
                "Mean FCT",
                "P90 FCT",
                "Max FCT",
                "Mean Slowdown",
                "PFC",
                "Bottleneck",
                "Max Q",
                "Q/Kmax",
                "Qlen Max",
                "Trace Records",
                "Warnings",
            ],
            rows,
        )
    )
    lines.append("")

    total_size_rows = sum(len(result["fct"]["by_size"]) for result in results)
    use_buckets = total_size_rows > 200
    lines.append("## FCT By Flow Size" + (" Bucket" if use_buckets else ""))
    lines.append("")
    rows = []
    for result in results:
        size_rows = result["fct"]["by_size_bucket"] if use_buckets else result["fct"]["by_size"]
        for row in size_rows:
            rows.append(
                [
                    result["name"],
                    str(row["size_bytes"]),
                    str(row["flows"]),
                    fmt_float(row["min_fct_ms"]),
                    fmt_float(row["median_fct_ms"]),
                    fmt_float(row["p90_fct_ms"]),
                    fmt_float(row["p99_fct_ms"]),
                    fmt_float(row["max_fct_ms"]),
                    fmt_float(row["median_slowdown"], 1) + "x",
                    fmt_float(row["p99_slowdown"], 1) + "x",
                    fmt_float(row["max_slowdown"], 1) + "x",
                ]
            )
    lines.append(
        markdown_table(
            [
                "Run",
                "Size" if use_buckets else "Size Bytes",
                "Flows",
                "Min FCT",
                "Median FCT",
                "P90 FCT",
                "P99 FCT",
                "Max FCT",
                "Median Slowdown",
                "P99 Slowdown",
                "Max Slowdown",
            ],
            rows,
        )
    )
    lines.append("")

    lines.append("## PFC And Bottleneck")
    lines.append("")
    rows = []
    for result in results:
        pfc = result["pfc"]
        bmax = result["bottleneck"].get("max_overall") or {}
        rows.append(
            [
                result["name"],
                str(pfc["events"]),
                str(pfc["pauses"]),
                str(pfc["resumes"]),
                "yes" if pfc["balanced"] else "no",
                str(pfc["unique_queues"]),
                fmt_float(pfc["first_event_ms"]),
                fmt_float(pfc["last_event_ms"]),
                (
                    f"sw{bmax.get('sw')} port{bmax.get('port')} pg{bmax.get('pg')}"
                    if bmax
                    else "n/a"
                ),
                fmt_float(
                    bmax.get("max_egress_bytes", 0) / 1000.0 if bmax else None,
                    1,
                    " KB",
                ),
                fmt_float(bmax.get("max_ratio") if bmax else None, 2),
                "yes" if bmax.get("ecn_seen") else "no",
                "yes" if bmax.get("pause_seen") else "no",
            ]
        )
    lines.append(
        markdown_table(
            [
                "Run",
                "Events",
                "Pause",
                "Resume",
                "Balanced",
                "Queues",
                "First ms",
                "Last ms",
                "Max Row",
                "Max Egress",
                "Q/Kmax",
                "ECN",
                "Pause",
            ],
            rows,
        )
    )
    lines.append("")

    lines.append("## Queue Distribution")
    lines.append("")
    rows = []
    for result in results:
        qlen = result["qlen"]
        qmax = qlen.get("max_port") or {}
        rows.append(
            [
                result["name"],
                str(qlen.get("dumps")),
                str(qlen.get("final_time_ns")),
                str(qlen.get("port_rows")),
                (
                    f"sw{qmax.get('sw')} port{qmax.get('port')}"
                    if qmax
                    else "n/a"
                ),
                fmt_float(qmax.get("mean_kb"), 2, " KB"),
                fmt_float(qmax.get("p95_kb"), 0, " KB"),
                fmt_float(qmax.get("p99_kb"), 0, " KB"),
                fmt_float(qmax.get("max_kb"), 0, " KB"),
            ]
        )
    lines.append(
        markdown_table(
            [
                "Run",
                "Dumps",
                "Final Time ns",
                "Ports",
                "Max Port",
                "Mean",
                "P95",
                "P99",
                "Max",
            ],
            rows,
        )
    )
    lines.append("")

    lines.append("## Trace Files")
    lines.append("")
    rows = []
    for result in results:
        trace = result["trace"]
        deep = trace.get("deep", {})
        rows.append(
            [
                result["name"],
                str(trace.get("size_bytes", 0)),
                str(trace.get("port_count", "n/a")),
                str(trace.get("records", "n/a")),
                str(deep.get("data", "n/a")),
                str(deep.get("ack_nack", "n/a")),
                str(deep.get("pfc", "n/a")),
                str(deep.get("host_records", "n/a")),
                str(deep.get("switch_records", "n/a")),
            ]
        )
    lines.append(
        markdown_table(
            [
                "Run",
                "Bytes",
                "Ports",
                "Records",
                "Data",
                "ACK/NACK",
                "PFC",
                "Host Records",
                "Switch Records",
            ],
            rows,
        )
    )
    lines.append("")

    warnings = [
        f"{result['name']}: {warning}"
        for result in results
        for warning in result.get("warnings", [])
    ]
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    if explain:
        lines.append("## Metric Meaning")
        lines.append("")
        lines.append("- `Drained`: final status reports all flows started and completed, with no active QPs, pending flows, bytes left, bytes in flight, or paused queues.")
        lines.append("- `FCT`: flow completion time from the flow start timestamp until `qp_finish`, reported in milliseconds.")
        lines.append("- `Standalone FCT`: the simulator's no-contention baseline for that flow size/path; `slowdown = FCT / standalone FCT`.")
        lines.append("- `PFC events`: pause plus resume records from `pfc.txt`; balanced pause/resume counts mean the run did not leave PFC asserted.")
        lines.append("- `Bottleneck max row`: the switch, port, and priority group with the largest sampled `max_egress_bytes / kmax` ratio, excluding PG 0.")
        lines.append("- `Q/Kmax`: maximum sampled egress queue divided by that port's configured ECN `kmax`; values above 1 mean the sampled queue exceeded the ECN max threshold.")
        lines.append("- `Qlen`: final cumulative queue-length distribution from `qlen.txt`; bins are total switch-port egress queue in KB, sampled at `qlen_mon_interval`.")
        lines.append("- `Trace records`: binary packet trace records after the SimSetting header. Runs with `enable_trace: 0` usually contain only the header.")
        lines.append("")
    return "\n".join(lines)


def render_csv(results: list[dict[str, Any]]) -> str:
    rows = [flat_summary(result) for result in results]
    fields = list(rows[0].keys()) if rows else []
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze HPCC algorithm-validation output artifacts."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory containing per-config output folders.",
    )
    parser.add_argument(
        "--configs",
        nargs="*",
        default=[],
        help="Optional config output folder names or paths to analyze.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "csv", "json"),
        default="markdown",
        help="Output format. Markdown is the default human report.",
    )
    parser.add_argument(
        "--deep-trace",
        action="store_true",
        help="Parse binary trace records to count packet/event classes. Slower for large traces.",
    )
    parser.add_argument(
        "--no-explain",
        action="store_true",
        help="Omit the metric glossary from Markdown output.",
    )
    parser.add_argument(
        "--write",
        type=Path,
        help="Write report to this path instead of stdout.",
    )
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    if not output_root.exists():
        print(f"ERROR: output root not found: {output_root}", file=sys.stderr)
        return 2

    run_paths = discover_runs(output_root, args.configs)
    missing = [path for path in run_paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"ERROR: run output not found: {path}", file=sys.stderr)
        return 2
    if not run_paths:
        print(f"ERROR: no run outputs found under {output_root}", file=sys.stderr)
        return 2

    results = [analyze_run(path, args.deep_trace) for path in run_paths]
    if args.format == "markdown":
        rendered = render_markdown(results, explain=not args.no_explain)
    elif args.format == "csv":
        rendered = render_csv(results)
    else:
        rendered = json.dumps(results, indent=2, sort_keys=True)

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered + ("\n" if not rendered.endswith("\n") else ""))
        print(f"Wrote {args.write}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
