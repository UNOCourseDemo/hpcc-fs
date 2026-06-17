#!/usr/bin/env python3
"""Per-flow throughput vs time from the binary trace (receiver-side Recv of data).

Decodes the .tr file (header: u32 len, len*(u16+u8+u64), u32 win; then 56-byte
TraceFormat records) and bins delivered wire bytes per flow over time, so we can SEE
how the long (multi-bottleneck) flow's rate evolves vs the cross flows.

Usage: trace_rates.py <config.yml> [--bin-ms 0.5] [--rows 40]
"""
import argparse
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_gap as ag  # reuse topology/flow parsing

REC = 56
IP_BASE = 0x0B000001


def node_of(ip):
    return (ip - IP_BASE) // 256


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--bin-ms", type=float, default=0.5)
    ap.add_argument("--rows", type=int, default=40)
    args = ap.parse_args()

    cfg = ag.resolve(args.config)
    if not os.path.exists(cfg):
        cfg = os.path.join(ag.HERE, "configs", os.path.basename(args.config))
    cap, adj = ag.parse_topology(ag.resolve(ag.cfg_get(cfg, "topology_file")))
    flows = ag.parse_flows(ag.resolve(ag.cfg_get(cfg, "flow_file")), adj)
    bn = min(cap.values())
    for fl in flows:
        fl["nbn"] = sum(1 for e in fl["links"] if cap[e] == bn)
    max_nbn = max(f["nbn"] for f in flows)
    label = {(f["src"], f["dst"]): ("LONG" if f["nbn"] == max_nbn else f"c{f['dst']}")
             for f in flows}
    flowkeys = [(f["src"], f["dst"]) for f in sorted(flows, key=lambda x: (-x["nbn"], x["id"]))]

    trf = ag.resolve(ag.cfg_get(cfg, "trace_output_file"))
    with open(trf, "rb") as f:
        data = f.read()
    (ln,) = struct.unpack_from("<I", data, 0)
    hdr = 4 + ln * 11 + 4
    nrec = (len(data) - hdr) // REC
    if (len(data) - hdr) % REC:
        print(f"WARNING: payload not 56-aligned (hdr={hdr}, size={len(data)})")
    binw = args.bin_ms * 1e6  # ns

    acc = collections.defaultdict(lambda: collections.defaultdict(int))  # key -> bin -> bytes
    off = hdr
    for _ in range(nrec):
        event = data[off + 27]
        l3 = data[off + 26]
        ntype = data[off + 29]
        if event == 0 and ntype == 0 and l3 == 0x11:  # Recv, host, UDP data
            t = struct.unpack_from("<Q", data, off)[0]
            sip = struct.unpack_from("<I", data, off + 16)[0]
            dip = struct.unpack_from("<I", data, off + 20)[0]
            size = struct.unpack_from("<H", data, off + 24)[0]
            acc[(node_of(sip), node_of(dip))][int(t // binw)] += size
        off += REC

    max_bin = max((b for d in acc.values() for b in d), default=0)
    step = max(1, (max_bin + 1 + args.rows - 1) // args.rows)
    fair = bn * 0.5 / 1e9  # max-min fair share on a 2-flow bottleneck (Gbps), for reference
    print(f"\n# per-flow goodput (Gbps), bin={args.bin_ms*step:.2f}ms, fair~{fair:.1f} Gbps/flow")
    print("t_ms   " + " ".join(f"{label[k]:>7}" for k in flowkeys))
    for b in range(0, max_bin + 1, step):
        row = []
        for k in flowkeys:
            byts = sum(acc[k].get(bb, 0) for bb in range(b, b + step))
            row.append(f"{byts * 8 / (binw * step):7.2f}")  # bytes*8/ns = Gbps
        print(f"{b*args.bin_ms:6.1f} " + " ".join(row))

    # whole-run averages
    print("\n# whole-run mean rate while active (Gbps):")
    for k in flowkeys:
        bins = acc[k]
        if not bins:
            continue
        span = (max(bins) - min(bins) + 1) * binw
        tot = sum(bins.values())
        print(f"  {label[k]:>7}: {tot*8/span:6.2f}  (active {span/1e6:.1f} ms)")


if __name__ == "__main__":
    main()
