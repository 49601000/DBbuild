import json

file_path = "c:/Users/info/MyAntigravity/02_hobby/04_qvt最適化ツール/tse_snapshot_day.ipynb"

# ノートブックを読み込む
with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# 各セルの内容を確認して修正する
for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        new_source = []
        changed = False
        for line in cell.get("source", []):
            # 未定義の root_path を db_path に書き換える
            if "root_path" in line and "db_path" not in line:
                new_source.append(line.replace("root_path", "db_path"))
                changed = True
            # 不要な import setup_path があれば削除する
            elif "import setup_path" in line:
                changed = True
                continue
            else:
                new_source.append(line)
        
        if changed:
            cell["source"] = new_source

# 修正したノートブックを保存する
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("ノートブックのパス修正が完了しました！")
