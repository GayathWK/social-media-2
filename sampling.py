import pandas as pd
import json
from pathlib import Path

ROOT = Path(".")  # run from project root
SAMPLES = ROOT / "data/samples"
SAMPLES.mkdir(exist_ok=True)

# 1. Comments sample — 200 per platform
df = pd.read_csv(ROOT / "data/processed/combined/combined_comments.csv")
sample = df.groupby("platform", group_keys=False).apply(
    lambda x: x.sample(min(200, len(x)), random_state=42)
)
sample.to_csv(SAMPLES / "combined_comments_sample.csv", index=False)
print(f"Comments sample: {len(sample)} rows")

# 2. Edges sample
with open(ROOT / "data/processed/combined/combined_edges.json") as f:
    edges = json.load(f)
edges_df = pd.DataFrame(edges)
edge_sample = edges_df.groupby("edge_type", group_keys=False).apply(
    lambda x: x.sample(min(200, len(x)), random_state=42)
)
edge_sample.to_json(SAMPLES / "combined_edges_sample.json", orient="records", indent=2)
print(f"Edges sample: {len(edge_sample)} rows")

# 3. Check total size
import os
total = sum(os.path.getsize(SAMPLES / f) for f in os.listdir(SAMPLES)) / (1024*1024)
print(f"Total samples size: {total:.2f} MB")