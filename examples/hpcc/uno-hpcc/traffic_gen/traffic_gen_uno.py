# python
import sys
import random
import math
import heapq
import argparse
from custom_rand import CustomRand

class Flow:
    def __init__(self, src: int, dst: int, size: int, t: float):
        self.src = src
        self.dst = dst
        self.size = size
        self.t = t

    def __str__(self) -> str:
        return f"%d %d 3 100 %d %.9f" % (self.src, self.dst, self.size, self.t)

def translate_bandwidth(b: str | None) -> float | None:
    if b is None:
        return None
    if not isinstance(b, str):
        return None
    b = b.strip().upper()
    if b.endswith('G'):
        return float(b[:-1]) * 1e9
    if b.endswith('M'):
        return float(b[:-1]) * 1e6
    if b.endswith('K'):
        return float(b[:-1]) * 1e3
    try:
        return float(b)
    except ValueError:
        return None

def poisson(lam: float) -> float:
    # exponential inter-arrival with mean lam
    return -math.log(1.0 - random.random()) * lam

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cdf", dest="cdf_file", default="uniform_distribution.txt",
                        help="the file of the traffic size cdf")
    parser.add_argument("-n", "--nhost", dest="nhost", type=int, required=True,
                        help="number of hosts")
    parser.add_argument("-l", "--load", dest="load", type=float, default=0.3,
                        help="traffic load fraction of link capacity (default 0.3)")
    parser.add_argument("-b", "--bandwidth", dest="bandwidth", default="10G",
                        help="bandwidth of host link (G/M/K), default 10G")
    parser.add_argument("-t", "--time", dest="time", type=float, default=10.0,
                        help="total run time in seconds (default 10)")
    parser.add_argument("-o", "--output", dest="output", default="tmp_traffic.txt",
                        help="output file")
    args = parser.parse_args()

    base_t = 2_000_000_000  # nanoseconds offset

    nhost = args.nhost
    load = args.load
    bandwidth = translate_bandwidth(args.bandwidth)
    total_time_ns = args.time * 1e9  # seconds -> ns
    output = args.output

    if bandwidth is None:
        print("bandwidth format incorrect", file=sys.stderr)
        sys.exit(1)

    # Read CDF
    try:
        with open(args.cdf_file, "r") as f:
            raw_lines = f.readlines()
    except Exception as e:
        print(f"failed to open cdf file: {e}", file=sys.stderr)
        sys.exit(1)

    cdf = []
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError:
            continue
        cdf.append([x, y])

    customRand = CustomRand()
    if not customRand.setCdf(cdf):
        print("Error: Not valid cdf", file=sys.stderr)
        sys.exit(1)

    avg = customRand.getAvg()
    # avg_inter_arrival in nanoseconds
    avg_inter_arrival = 1.0 / (bandwidth * load / 8.0 / avg) * 1e9
    n_flow_estimate = int(total_time_ns / avg_inter_arrival * nhost)

    n_flow = 0
    # initial event times per host
    host_list = [(base_t + int(poisson(avg_inter_arrival)), i) for i in range(nhost)]
    heapq.heapify(host_list)

    # open file for read/write so we can overwrite the first line later and truncate
    with open(output, "w+") as ofile:
        ofile.write(f"{n_flow_estimate}\n")
        ofile.flush()

        while host_list:
            t, src = heapq.heappop(host_list)
            if t > total_time_ns + base_t:
                # this host has no more events within time window
                continue

            # choose destination != src
            dst = random.randint(0, nhost - 1)
            while dst == src and nhost > 1:
                dst = random.randint(0, nhost - 1)

            size = int(customRand.rand())
            if size <= 0:
                size = 1

            # write flow: src dst 3 100 size time_in_seconds (9 decimals)
            time_sec = t * 1e-9
            ofile.write(f"{src} {dst} 3 100 {size} {time_sec:.9f}\n")
            n_flow += 1

            # schedule next event for this host
            inter_t = int(poisson(avg_inter_arrival))
            next_t = t + inter_t
            if next_t <= total_time_ns + base_t:
                heapq.heappush(host_list, (next_t, src))

        # overwrite header with actual count and truncate rest
        ofile.seek(0)
        ofile.write(f"{n_flow}\n")
        ofile.truncate()

if __name__ == "__main__":
    main()