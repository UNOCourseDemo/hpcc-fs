import sys
import random
import math
import heapq
import argparse
import os
from piecewise_random import DistributionManager, DistName

# --- Helper Classes & Functions ---

class Flow:
    def __init__(self, src, dst, size, t):
        self.src, self.dst, self.size, self.t = src, dst, size, t

    def __str__(self):
        return "%d %d 3 100 %d %.9f" % (self.src, self.dst, self.size, self.t)

def translate_bandwidth(b_str):
    if not b_str:
        return None
    if type(b_str) != str:
        return float(b_str)

    suffix = b_str[-1].upper()
    value = b_str[:-1]

    try:
        if suffix == 'G':
            return float(value) * 1e9
        elif suffix == 'M':
            return float(value) * 1e6
        elif suffix == 'K':
            return float(value) * 1e3
        else:
            return float(b_str)
    except ValueError:
        return None

def poisson(lam):
    # Generates inter-arrival time based on Poisson process
    # Note: random.random() can return 0.0, math.log(0) is undefined.
    # We use 1.0 - random() to ensure range (0.0, 1.0]
    r = 1.0 - random.random()
    return -math.log(r) * lam

# --- Main Execution ---

if __name__ == "__main__":
    # 1. Parse Arguments using argparse (Python 3 standard)
    parser = argparse.ArgumentParser(description="Generate network traffic flows based on custom CDFs.")

    parser.add_argument("-c", "--conf", dest="json_file", default="./distributions/distributions.json",
                        help="The JSON file containing distribution definitions.")

    parser.add_argument("-d", "--dist", dest="dist_name", default="WEB_SEARCH_DIST",
                        help="The specific distribution name to use (e.g., GoogleRPC2008, AliStorage2019).")

    parser.add_argument("-n", "--nhost", dest="nhost", type=int, required=True,
                        help="Number of hosts.")

    parser.add_argument("-l", "--load", dest="load", type=float, default=0.3,
                        help="Percentage of network load (0.0 - 1.0). Default 0.3.")

    parser.add_argument("-b", "--bandwidth", dest="bandwidth", default="10G",
                        help="Bandwidth of host link (e.g., 10G, 100M). Default 10G.")

    parser.add_argument("-t", "--time", dest="time", type=float, default=10,
                        help="Total run time in seconds. Default 10.")

    parser.add_argument("-o", "--output", dest="output", default="tmp_traffic.txt",
                        help="Output file path.")

    args = parser.parse_args()

    # 2. Configuration & Constants
    base_t = 2000000000 # Start time offset (ns)
    nhost = args.nhost
    load = args.load
    total_time_ns = args.time * 1e9

    bandwidth_bps = translate_bandwidth(args.bandwidth)
    if bandwidth_bps is None:
        print("Error: Bandwidth format incorrect. Use format like '10G', '100M'.")
        sys.exit(1)

    # 3. Load Distribution from JSON
    print(f"Loading distributions from {args.json_file}...")
    try:
        DistributionManager.load(args.json_file)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.json_file}' not found.")
        sys.exit(1)

    # 4. Select the specific distribution
    # We try to match the input string to the Enum member names or values
    target_dist_enum = None

    # Try to find by Value (e.g., "AliStorage2019.txt" logic from before, or clean names)
    # Or find by Enum Key (e.g., ALI_STORAGE)
    for d in DistName:
        # Check against Enum name (ALI_STORAGE) or the value defined in Enum (ALI_STORAGE_2019)
        if args.dist_name.upper() == d.name or args.dist_name == d.value:
            target_dist_enum = d
            break

    # Fallback: If not in Enum, check if the loader loaded it as a raw string key
    # (This depends on if your DistributionManager allows dynamic keys.
    # Based on previous code, it used strict Enums, so we must match the Enum).

    if not target_dist_enum:
        print(f"Error: Distribution '{args.dist_name}' not found in DistName enum.")
        print("Available options:", [d.name for d in DistName])
        sys.exit(1)

    rng = DistributionManager.get(target_dist_enum)
    if not rng:
        print(f"Error: Distribution '{args.dist_name}' was not found in the JSON file.")
        sys.exit(1)

    print(f"Using distribution: {target_dist_enum.name}")

    # 5. Traffic Generation Logic
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    tmp_output = f"{args.output}.tmp.{os.getpid()}"

    try:
        with open(tmp_output, "w") as ofile:
            # Calculate Average Flow Size (in bytes)
            avg_size = rng.get_average()
            if avg_size <= 0:
                print("Error: Distribution average size is <= 0.")
                sys.exit(1)

            # Calculate Inter-arrival time (ns)
            # Formula: Time to send one avg flow = (avg_size * 8 bits) / (bandwidth * load)
            # avg_inter_arrival = (avg_size * 8.0) / (bandwidth_bps * load) * 1e9
            # (This is equivalent to the original 1/(.../avg) formula)
            avg_inter_arrival = 1.0 / (bandwidth_bps * load / 8.0 / avg_size) * 1e9

            n_flow_estimate = int(total_time_ns / avg_inter_arrival * nhost)

            print(f"  Avg Flow Size: {avg_size:.2f} bytes")
            print(f"  Avg Inter-arrival: {avg_inter_arrival:.2f} ns")
            print(f"  Estimated Flows: {n_flow_estimate}")

            # Reserve a fixed-width header so the actual count can be rewritten
            # safely even when it has fewer digits than the estimate.
            ofile.write(f"{0:20d}\n")

            # Initialize Host Events
            # host_list is a heap of (next_event_time, host_id)
            host_list = [(base_t + int(poisson(avg_inter_arrival)), i) for i in range(nhost)]
            heapq.heapify(host_list)

            n_flow = 0

            while len(host_list) > 0:
                t, src = host_list[0]

                # Calculate time for NEXT event for this host
                inter_t = int(poisson(avg_inter_arrival))
                next_time = t + inter_t

                # Pick destination
                dst = random.randint(0, nhost - 1)
                while dst == src:
                    dst = random.randint(0, nhost - 1)

                # Check if we exceeded simulation time
                if next_time > total_time_ns + base_t:
                    heapq.heappop(host_list) # Remove host from simulation
                else:
                    # Generate Flow Size using our new class
                    size = int(rng.get_random_value())
                    if size <= 0:
                        size = 1

                    n_flow += 1

                    # Write Flow: src dst type(3) prio(100) size time(sec)
                    ofile.write(f"{src} {dst} 3 100 {size} {t * 1e-9:.9f}\n")

                    # Update heap with next event for this host
                    heapq.heapreplace(host_list, (next_time, src))

            # Rewind to top and write actual flow count. os.replace below makes
            # generation atomic: an interrupted run leaves the previous file intact.
            ofile.seek(0)
            ofile.write(f"{n_flow:20d}\n")
            print(f"Done. Generated {n_flow} flows in '{args.output}'.")
        os.replace(tmp_output, args.output)

    except IOError as e:
        try:
            if os.path.exists(tmp_output):
                os.unlink(tmp_output)
        except OSError:
            pass
        print(f"File Error: {e}")
        sys.exit(1)
