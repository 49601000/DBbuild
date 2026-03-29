import json

file_path = "c:/Users/info/MyAntigravity/02_hobby/04_qvt最適化ツール/tse_snapshot_day.ipynb"

with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

changed = False
for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        source = cell.get("source", [])
        # Cell 11 の 'csv_files = sorted(Path(OUTPUT_DIR).glob('snapshot_*.csv'))' などを探す
        for i, line in enumerate(source):
            if "csv_files =" in line and "Path" in line:
                # すでに import pathlib があるかチェック
                if not any("import Path" in s or "import pathlib" in s for s in source):
                    source.insert(i, "from pathlib import Path\n")
                    changed = True
                    break
        if changed:
            cell["source"] = source
            break

# もし上の中に見つからなくても、とりあえず最初のコードセルに追記する安全策
if not changed:
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            if not any("from pathlib import Path" in line for line in cell.get("source", [])):
                cell.get("source", []).insert(0, "from pathlib import Path\n")
            changed = True
            break

if changed:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print("✅ `Path` のインポートをノートブックに追加しました！")
else:
    print("すでに設定されています。")
