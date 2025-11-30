"""
deduplicate_links.py

Reads graph.json from the current folder, removes duplicate links
(considering undirected duplicates and self-links), and saves the cleaned file.
"""

import os
import json

def main():
    json_path = "graph.json"

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"No file named '{json_path}' found in this folder.")

    # Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    nodes = graph.get("nodes", [])
    links = graph.get("links", [])

    # Remove duplicates and self-links
    seen_pairs = set()
    deduped_links = []

    for link in links:
        # Normalize IDs (string + trim)
        src = str(link.get("source")).strip()
        tgt = str(link.get("target")).strip()

        # Skip self links
        if src == tgt:
            continue

        # Undirected pairing
        pair = tuple(sorted([src, tgt]))

        if pair not in seen_pairs:
            deduped_links.append(link)
            seen_pairs.add(pair)

    # Update graph
    graph["links"] = deduped_links

    # Save cleaned JSON
    output_path = "graph.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"✅ Done. Original links: {len(links)}, Deduped: {len(deduped_links)}")
    print(f"Output saved to {output_path}")

if __name__ == "__main__":
    main()
