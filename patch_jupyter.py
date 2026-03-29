import os
import json

file_path = "c:/Users/info/MyAntigravity/02_hobby/04_qvt最適化ツール/tse_snapshot_day.ipynb"

with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        changed = False
        sources = cell.get("source", [])
        new_sources = []
        for line in sources:
            if 'print(f"新住所登録完了！現在のルート: {root_path}")\n' == line:
                new_sources.append('print(f"新住所登録完了！現在のルート: {db_path}")\n')
                changed = True
            elif "import yfinance as yf\n" == line:
                new_sources.append(line)
                new_sources.append("import time\n")
                new_sources.append("import warnings\n")
                new_sources.append("from pathlib import Path\n")
                new_sources.append("from datetime import timedelta\n")
                new_sources.append("from typing import List, Dict, Optional, Any\n")
                changed = True
            else:
                new_sources.append(line)
        if changed:
            cell["source"] = new_sources

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Patch applied to notebook successfully!")
