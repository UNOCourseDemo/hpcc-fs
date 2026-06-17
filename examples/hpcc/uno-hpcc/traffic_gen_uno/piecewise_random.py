import json
from enum import Enum
from typing import Dict, List, Tuple, Optional
import random
import bisect

# --- 1. The Enum Definition ---
class DistName(Enum):
    ALI_STORAGE = "ALI_STORAGE_2019"
    FB_HDP = "FB_HDP_DIST"
    GOOGLE_RPC = "GOOGLE_RPC_2008"
    WEB_SEARCH = "WEB_SEARCH_DIST"

def _validate_cdf(cdf: List[Tuple[float, float]]) -> bool:
    """Ensures CDF starts at 0%, ends at 100%, and is monotonic."""
    if not cdf or len(cdf) < 2: return False
    if cdf[0][1] != 0: return False
    if cdf[-1][1] != 100: return False

    # Check for strict ordering
    for i in range(1, len(cdf)):
        prev_val, prev_perc = cdf[i-1]
        curr_val, curr_perc = cdf[i]
        if curr_perc <= prev_perc or curr_val <= prev_val:
            return False
    return True


def _interpolate(x_start, x_end, y_start, y_end, x_target) -> float:
    """Helper for linear interpolation between two points."""
    if x_end == x_start: return y_start
    slope = (y_end - y_start) / (x_end - x_start)
    return y_start + slope * (x_target - x_start)


class PiecewiseRandom:
    """
    A random number generator based on a custom Piecewise Linear CDF.
    Performs Inverse Transform Sampling to generate non-uniform random numbers.
    """

    def __init__(self, cdf_points: Optional[List[Tuple[float, float]]] = None):
        """
        Args:
            cdf_points: List of (value, percentile) tuples.
                        Example: [(10, 0), (50, 50), (100, 100)]
        """
        self._cdf_points = []
        self._values = []      # The X axis (domain)
        self._percentiles = [] # The Y axis (probabilities 0-100)

        if cdf_points:
            self.set_cdf(cdf_points)

    def set_cdf(self, cdf_points: List[Tuple[float, float]]) -> bool:
        """Validates and loads the CDF data."""
        if not _validate_cdf(cdf_points):
            raise ValueError("Invalid CDF: Must be strictly increasing and cover 0-100%.")

        self._cdf_points = cdf_points
        # Unzip into two lists for faster binary search
        self._values, self._percentiles = zip(*cdf_points)
        return True

    def get_random_value(self) -> float:
        """Generates a random value based on the custom distribution."""
        if not self._cdf_points: return 0.0
        r = random.uniform(0, 100)
        return self.get_value_from_percentile(r)

    def get_percentile_from_value(self, value: float) -> float:
        """
        Given a value (X), find its percentile (Y).
        Uses Binary Search (bisect) for O(log N) performance.
        """
        if not self._cdf_points: return -1
        # Check boundaries
        if value < self._values[0]: return 0.0
        if value > self._values[-1]: return 100.0

        # Find insertion point
        idx = bisect.bisect_right(self._values, value)

        # Determine surrounding points
        i_low = max(0, idx - 1)
        i_high = idx

        return _interpolate(
            x_start=self._values[i_low], x_end=self._values[i_high],
            y_start=self._percentiles[i_low], y_end=self._percentiles[i_high],
            x_target=value
        )

    def get_value_from_percentile(self, percentile: float) -> float:
        """
        Given a percentile (Y), find the corresponding value (X).
        Uses Binary Search.
        """
        if not self._cdf_points: return 0.0

        # Clamp percentile to valid range
        percentile = max(0.0, min(100.0, percentile))

        # Find insertion point based on percentiles
        idx = bisect.bisect_right(self._percentiles, percentile)

        i_low = max(0, idx - 1)
        i_high = idx

        return _interpolate(
            x_start=self._percentiles[i_low], x_end=self._percentiles[i_high],
            y_start=self._values[i_low], y_end=self._values[i_high],
            x_target=percentile
        )

    def get_average(self) -> float:
        """Calculates the Mean (Expected Value) by integrating the inverse CDF."""
        if not self._cdf_points: return 0.0

        area = 0.0
        # Trapezoidal rule integration
        for i in range(1, len(self._cdf_points)):
            x0, p0 = self._cdf_points[i-1]
            x1, p1 = self._cdf_points[i]

            # (Average Value in segment) * (Probability of segment)
            segment_avg = (x0 + x1) / 2.0
            segment_prob = (p1 - p0)
            area += segment_avg * segment_prob

        return area / 100.0

    def get_integral_up_to_percentile(self, percentile: float) -> float:
        """
        Calculates the partial expectation up to a specific percentile.
        Useful for Expected Shortfall calculations.
        """
        if not self._cdf_points: return 0.0
        percentile = min(100.0, percentile)

        area = 0.0
        for i in range(1, len(self._cdf_points)):
            x0, p0 = self._cdf_points[i-1]
            x1, p1 = self._cdf_points[i]

            if percentile <= p0:
                break

            # If our target percentile is inside this segment, clip the segment
            if percentile < p1:
                # Calculate the specific X at the cutoff percentile
                x_cutoff = self.get_value_from_percentile(percentile)
                current_p1 = percentile
                current_x1 = x_cutoff
            else:
                # Use the full segment
                current_p1 = p1
                current_x1 = x1

            segment_avg = (x0 + current_x1) / 2.0
            segment_prob = (current_p1 - p0)
            area += segment_avg * segment_prob

        return area / 100.0
class DistributionManager:
    _loaded_dists: Dict[DistName, PiecewiseRandom] = {}

    @classmethod
    def load(cls, filepath="distributions.json"):
        """Loads the JSON and populates the dictionary."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        for dist_enum in DistName:
            key = dist_enum.value
            if key in data:
                # Convert list-of-lists to list-of-tuples
                points = [tuple(p) for p in data[key]]
                cls._loaded_dists[dist_enum] = PiecewiseRandom(points)
            else:
                print(f"Warning: {key} not found in JSON file.")

    @classmethod
    def get(cls, name: DistName) -> Optional[PiecewiseRandom]:
        """Access a distribution safely using the Enum."""
        return cls._loaded_dists.get(name)

def example_manager():
    # 1. Load Data
    DistributionManager.load("./distributions/distributions.json")

    for dist in DistName:
        print(f"Loaded distribution: {dist.name}")

        # 2. Select a distribution using the Enum (Auto-complete friendly!)
        selected_dist = dist
        rng = DistributionManager.get(selected_dist)

        if rng:
            print(f"--- Simulating {selected_dist.name} ---")
            print(f"Sample 1: {rng.get_random_value():.2f}")
            print(f"Sample 2: {rng.get_random_value():.2f}")
            print(f"99th Percentile Value: {rng.get_value_from_percentile(99):.2f}")

# --- Detailed Usage Examples ---
def example_usage():
    print("--- 1. SCENARIO: Server Latency Simulation (Long Tail) ---")
    # We want to model server response times:
    # - 0% of requests are faster than 10ms
    # - 80% of requests are very fast (between 10ms and 50ms)
    # - 95% of requests are okay (up to 200ms)
    # - 100% of requests are finished by 1000ms (the long tail of timeouts)

    latency_cdf = [
        (10, 0),    # Min value
        (50, 80),   # 80th percentile is 50ms
        (200, 95),  # 95th percentile is 200ms
        (1000, 100) # Max value
    ]

    sim = PiecewiseRandom(latency_cdf)
    print("CDF Loaded successfully.")

    print("\n--- 2. Generating Random Values ---")
    print("Simulating 5 requests:")
    for i in range(5):
        val = sim.get_random_value()
        print(f"  Request {i+1}: {val:.2f} ms")

    print("\n--- 3. Statistical Analysis ---")
    # The 'Median' is the 50th percentile.
    median_latency = sim.get_value_from_percentile(50)

    # The 'Mean' accounts for the heavy tail (the 1000ms outliers).
    mean_latency = sim.get_average()

    print(f"Median Latency (50%): {median_latency:.2f} ms (Typical User Experience)")
    print(f"Mean Latency (Avg):   {mean_latency:.2f} ms (Impacted by outliers)")

    if mean_latency > median_latency:
        print(">> Note: The Mean is higher than the Median, confirming a 'right-skewed' distribution.")

    print("\n--- 4. Reverse Lookup (Percentile from Value) ---")
    target_ms = 100
    perc = sim.get_percentile_from_value(target_ms)
    print(f"What % of users get a response faster than {target_ms}ms?")
    print(f"  Answer: {perc:.2f}%")

    print("\n--- 5. Advanced: Conditional Expectation ---")
    # Sometimes we want to know: "What is the average latency of the FASTEST 80% of requests?"
    # We use get_integral_up_to_percentile(80) which gives the weighted sum,
    # then divide by the probability (0.80) to get the average.

    cutoff_percentile = 80
    integral = sim.get_integral_up_to_percentile(cutoff_percentile)
    avg_of_fastest = integral / (cutoff_percentile / 100.0)

    print(f"Average latency of the fastest {cutoff_percentile}% of users: {avg_of_fastest:.2f} ms")

    print("\n--- 6. Verification: Text Histogram ---")
    # Let's generate 10,000 values and see where they land to prove it works.
    buckets = {"< 50ms": 0, "50-200ms": 0, "> 200ms": 0}
    total_samples = 10000

    for _ in range(total_samples):
        v = sim.get_random_value()
        if v <= 50:
            buckets["< 50ms"] += 1
        elif v <= 200:
            buckets["50-200ms"] += 1
        else:
            buckets["> 200ms"] += 1

    print(f"Generated {total_samples} samples:")
    print(f"  < 50ms:   {buckets['< 50ms']} (Expected ~8000)")
    print(f"  50-200ms: {buckets['50-200ms']} (Expected ~1500)")
    print(f"  > 200ms:  {buckets['> 200ms']}  (Expected ~500)")

if __name__ == "__main__":
    example_manager()