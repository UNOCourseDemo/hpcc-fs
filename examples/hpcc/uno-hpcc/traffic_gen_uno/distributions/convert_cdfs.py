import json
import re

def parse_cdf_content(content):
    """
    Parses raw CDF text content into a list of [value, percentile] pairs.
    Handles irregular whitespace, newlines, and '' tags.
    """
    # 1. Remove '' tags
    clean_content = re.sub(r'\'', '', content)

    # 2. Split by any whitespace (newlines, spaces, tabs)
    tokens = clean_content.split()

    # 3. Convert to floats
    try:
        numbers = [float(t) for t in tokens]
    except ValueError as e:
        print(f"Error parsing numbers: {e}")
        return []

    # 4. Pair them up: [Value, Percentile]
    points = []
    for i in range(0, len(numbers), 2):
        if i + 1 < len(numbers):
            val = numbers[i]
            perc = numbers[i+1]
            points.append([val, perc])

    return points

def main():
    # Map friendly names (for the JSON keys) to filenames
    files_to_process = {
        "ALI_STORAGE_2019": "AliStorage2019.txt",
        "FB_HDP_DIST": "FbHdp_distribution.txt",
        "GOOGLE_RPC_2008": "GoogleRPC2008.txt",
        "WEB_SEARCH_DIST": "WebSearch_distribution.txt"
    }

    output_data = {}

    for key, filename in files_to_process.items():
        try:
            with open(filename, 'r') as f:
                raw_content = f.read()

            points = parse_cdf_content(raw_content)

            # Validation: Ensure it's not empty
            if points:
                output_data[key] = points
                print(f"✅ Processed {filename}: {len(points)} points found.")
            else:
                print(f"⚠️ Warning: {filename} resulted in 0 points.")

        except FileNotFoundError:
            print(f"❌ Error: File '{filename}' not found.")

    # Save to JSON
    output_filename = "distributions.json"
    with open(output_filename, 'w') as f:
        json.dump(output_data, f, indent=None) # indent=None keeps file size smaller

    print(f"\n🎉 Success! Saved all distributions to '{output_filename}'")

if __name__ == "__main__":
    main()