import os
import json
from pathlib import Path

BASE_DIR = Path(r"C:\Users\info\MyAntigravity\02_hobby\04_qvt最適化ツール")

def patch_notebook_percent_run(notebook_path: Path):
    if not notebook_path.exists():
        return
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    changed = False
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            new_source = []
            for line in cell.get("source", []):
                if "%run fetch_jquants_cache.py" in line:
                    new_source.append(line.replace("%run fetch_jquants_cache.py", "%run ../02_データベースbuild/fetch_jquants_cache.py"))
                    changed = True
                else:
                    new_source.append(line)
            if new_source != cell.get("source", []):
                cell["source"] = new_source
    if changed:
        with open(notebook_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, ensure_ascii=False, indent=1)
        print(f"✅ Patched %run in {notebook_path.name}")

# 1 & 2. Notebooks を修正する
patch_notebook_percent_run(BASE_DIR / "tse_snapshot_day.ipynb")
patch_notebook_percent_run(BASE_DIR / "backtest_export.ipynb")

# 3. app/build_tse_master.py を修正する
b_path = BASE_DIR / "app" / "build_tse_master.py"
if b_path.exists():
    text = b_path.read_text(encoding="utf-8")
    
    # すでに修正済みかチェック
    if "fallback: 02_データベースbuild" not in text:
        fallback_code = """
    # fallback: 02_データベースbuild (04_qvt最適化ツール用)
    db_build = Path(__file__).resolve().parent.parent.parent / "02_データベースbuild"
    if (db_build / "core").is_dir():
        return db_build

    raise RuntimeError("""
        text = text.replace("    raise RuntimeError(", fallback_code)
        b_path.write_text(text, encoding="utf-8")
        print(f"✅ Patched fallbacks in build_tse_master.py")

print("All patches applied.")
