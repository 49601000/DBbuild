import json

file_path = r"c:\Users\info\MyAntigravity\02_hobby\04_qvt最適化ツール\tse_snapshot_day.ipynb"

def definitive_fix():
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # 必要なすべてのインポート定型句
    required_imports = [
        "import sys\n",
        "import os\n",
        "import pandas as pd\n",
        "import numpy as np\n",
        "import yfinance as yf\n",
        "import time\n",
        "import warnings\n",
        "from pathlib import Path\n",
        "from datetime import timedelta, datetime\n",
        "from typing import List, Dict, Optional, Any\n"
    ]

    found_import_cell = False
    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'code':
            source = cell.get('source', [])
            
            # すでに root_path を db_path に変える処理は refine_notebook.py でやったはずだが念押し
            source = [line.replace('root_path', 'db_path') for line in source]
            
            # import sys があるセルを「メイン・インポート・セル」とみなしてインポートを注入
            if any("import sys" in line for line in source) and not found_import_cell:
                # 既存のインポート関係を一旦除外して、先頭にきれいに入れ直す
                non_import_lines = [line for line in source if not line.strip().startswith(('import ', 'from '))]
                cell['source'] = required_imports + ["\n"] + non_import_lines
                found_import_cell = True
            else:
                cell['source'] = source
            
            # 出力記録を完全に消去して実行状態をリセット
            cell['outputs'] = []
            cell['execution_count'] = None

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    definitive_fix()
    print("Notebook fixed with definitive imports!")
