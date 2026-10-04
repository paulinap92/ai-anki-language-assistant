from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
if not root.exists():
    raise SystemExit(f"Package folder not found: {root}")

rows = []
for path in root.rglob("*"):
    if path.is_file():
        rel = path.relative_to(root)
        rows.append((len(str(rel)), str(rel)))

rows.sort(reverse=True)
maximum = rows[0][0] if rows else 0

print(f"Maximum relative path length: {maximum}")
print("Longest paths:")
for length, rel in rows[:10]:
    print(f"{length:3d}  {rel}")

if maximum > 180:
    raise SystemExit(
        f"Package contains relative paths longer than 180 characters: {maximum}"
    )
