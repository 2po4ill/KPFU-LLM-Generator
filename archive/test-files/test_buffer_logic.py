"""
Test to understand the buffer logic
"""

# Simulate what LLM returns
llm_response_strings = "36-38, 89-90"

# Parse ranges
import re

ranges = []
parts = llm_response_strings.split(',')

for part in parts:
    part = part.strip()
    
    if '-' in part:
        match = re.match(r'(\d+)-(\d+)', part)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            ranges.append((start, end))
            print(f"Parsed range: {start}-{end}")

print(f"\nParsed ranges: {ranges}")

# Add buffer
buffer_pages = 1
pages = set()

for start, end in ranges:
    # Add all pages in range
    pages.update(range(start, end + 1))
    print(f"  Range {start}-{end}: added pages {list(range(start, end + 1))}")
    
    # Add buffer pages after range
    buffer_added = list(range(end + 1, end + 1 + buffer_pages))
    pages.update(buffer_added)
    print(f"  Buffer after {end}: added pages {buffer_added}")

final_pages = sorted(pages)
print(f"\nFinal pages: {final_pages}")
print(f"Expected: [36, 37, 38, 39, 89, 90, 91]")
