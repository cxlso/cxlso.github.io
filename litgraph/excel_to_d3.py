"""
excel_to_d3.py

Auto-detects the first Excel (.xlsx) file in the current folder
and converts it to a D3-ready JSON file.

Output filename automatically matches input:
e.g. reading_list.xlsx → graph.json
"""

import os
import glob
import json
import pandas as pd
from collections import defaultdict

# -----------------------------------------
# Core conversion logic
# -----------------------------------------

def parse_links_field(cell):
    if pd.isna(cell):
        return []
    txt = str(cell).strip()
    if not txt:
        return []
    # IDs separated ONLY by semicolons
    return [p.strip() for p in txt.split(";") if p.strip()]

def normalize_id(x):
    if pd.isna(x):
        return None
    return str(x).strip()

def build_graph(df):
    id_col   = "ID"
    link_col = "Link"
    meta_cols = ["Theme","category","author","title","year","publisher","URL","Description"]

    df[id_col] = df[id_col].map(normalize_id)

    # Create nodes
    nodes = {}
    for _, row in df.iterrows():
        nid = row.get(id_col)
        if not nid:
            continue

        node = {"id": nid}
        for m in meta_cols:
            if m in df.columns:
                val = row.get(m)
                if pd.isna(val):
                    val = None
                else:
                    # Convert Description to HTML paragraphs
                    if m == "Description":
                        paragraphs = [p.strip() for p in str(val).split("\n") if p.strip()]
                        val = "".join(f"<p>{p}</p>" for p in paragraphs)
                node[m] = val

        nodes[nid] = node

    # Create links (with aggregation)
    link_counter = defaultdict(int)

    for _, row in df.iterrows():
        src = normalize_id(row.get(id_col))
        if not src:
            continue

        targets = parse_links_field(row.get(link_col) if link_col in df.columns else None)

        for t in targets:
            tgt = normalize_id(t)
            if not tgt:
                continue

            link_counter[(src, tgt)] += 1

            # Create stub nodes if missing
            if tgt not in nodes:
                nodes[tgt] = {"id": tgt}

    links = [
        {"source": s, "target": t, "value": w}
        for (s, t), w in link_counter.items()
    ]

    return list(nodes.values()), links

# -----------------------------------------
# Auto-detection + execution
# -----------------------------------------

def main():

    excel_files = glob.glob("*.xlsx")

    if not excel_files:
        raise FileNotFoundError("No Excel (.xlsx) files found in this folder.")

    excel_path = excel_files[0]
    print(f"📄 Found Excel file: {excel_path}")

    base_name = os.path.splitext(excel_path)[0]
    json_path = "graph" + ".json"

    print(f"🔁 Converting → {json_path}")

    # Load Excel
    df = pd.read_excel(excel_path, dtype=object)
    df.columns = [c.strip() if isinstance(c,str) else c for c in df.columns]

    # Build graph
    nodes, links = build_graph(df)

    graph = {
        "nodes": nodes,
        "links": links
    }

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"✅ Done:")
    print(f"   Nodes → {len(nodes)}")
    print(f"   Links → {len(links)}")
    print(f"   Output → {json_path}")

if __name__ == "__main__":
    main()
