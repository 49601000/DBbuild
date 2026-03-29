import json
import os
from pathlib import Path

def fix_notebook():
    file_path = r"c:\Users\info\MyAntigravity\02_hobby\04_qvt最適化ツール\tse_snapshot_day.ipynb"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Prepare missing cells
    # Cell 2: Path setup & imports
    cell_imports = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ===================================================\n",
            "# Cell 2: Path setup & imports\n",
            "# ===================================================\n",
            "\n",
            "import os, sys, time, warnings, traceback\n",
            "from datetime import datetime, timedelta\n",
            "from pathlib import Path\n",
            "from typing import Optional, Dict, Any, List\n",
            "\n",
            "import pandas as pd\n",
            "import numpy as np\n",
            "import yfinance as yf\n",
            "\n",
            "warnings.filterwarnings('ignore')\n",
            "\n",
            "# Add 02_データベースbuild to sys.path to access modules and build_tse_master\n",
            "current_dir = Path().resolve()\n",
            "db_build_dir = (current_dir.parent / '02_データベースbuild').resolve()\n",
            "if str(db_build_dir) not in sys.path:\n",
            "    sys.path.insert(0, str(db_build_dir))\n",
            "\n",
            "print(f\"Database build directory added to path: {db_build_dir}\")\n",
            "\n",
            "try:\n",
            "    # checkSIGNALs modules from 02_データベースbuild\n",
            "    from modules.q_logic    import score_quality\n",
            "    from modules.valuation  import score_valuation\n",
            "    from modules.t_logic    import compute_t_metrics\n",
            "    from modules.indicators import (\n",
            "        calc_moving_averages, calc_bollinger_bands, calc_rsi, calc_slope\n",
            "    )\n",
            "    # TSE master builder\n",
            "    from build_tse_master import build_tse_master\n",
            "    print(\"Modules imported successfully!\")\n",
            "except ImportError as e:\n",
            "    print(f\"Error importing modules: {e}\")\n",
            "    print(\"Please check if '02_データベースbuild' directory exists and contains 'modules' and 'build_tse_master.py'\")\n",
            "\n",
            "Path(OUTPUT_DIR).mkdir(exist_ok=True)\n",
            "print('Imports and output directory setup done.')\n"
        ]
    }

    # Cell 3: Build TSE ticker universe
    cell_tickers = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ===================================================\n",
            "# Cell 3: Build TSE ticker universe\n",
            "# ===================================================\n",
            "\n",
            "_master_local = Path(OUTPUT_DIR) / 'tse_master_latest.csv'\n",
            "\n",
            "if not REFRESH_MASTER and _master_local.exists():\n",
            "    print(f'Reusing existing master: {_master_local}')\n",
            "    master_df = pd.read_csv(_master_local, encoding='utf-8-sig')\n",
            "else:\n",
            "    print('Running build_tse_master...')\n",
            "    try:\n",
            "        result = build_tse_master(\n",
            "            market_scope=MARKET_SCOPE,\n",
            "            refresh_pool=REFRESH_MASTER,\n",
            "            sleep_sec=0.5,\n",
            "            use_yfinance=True,\n",
            "            save_csv=True,\n",
            "            output_dir=OUTPUT_DIR,\n",
            "        )\n",
            "        master_df = result['master_df']\n",
            "        print(result['summary'])\n",
            "    except NameError:\n",
            "        print(\"build_tse_master is not defined. Make sure Cell 2 ran successfully.\")\n",
            "        master_df = pd.DataFrame()\n",
            "\n",
            "if not ('master_df' in locals() and not master_df.empty):\n",
            "    print(\"Error: master_df is empty or not defined. Cannot build TICKERS list.\")\n",
            "    TICKERS = []\n",
            "else:\n",
            "    print(f'Master rows: {len(master_df)}')\n",
            "\n",
            "    # -- market filter --\n",
            "    if MARKET_SCOPE != 'all' and 'market' in master_df.columns:\n",
            "        scope_keywords = {\n",
            "            'prime':    ['Prime Market', 'prime', 'PRIME'],\n",
            "            'standard': ['Standard Market', 'standard', 'STANDARD'],\n",
            "            'growth':   ['Growth Market', 'growth', 'GROWTH'],\n",
            "        }\n",
            "        kws = scope_keywords.get(MARKET_SCOPE, [])\n",
            "        if kws:\n",
            "            mask = master_df['market'].str.contains('|'.join(kws), na=False, case=False)\n",
            "            master_df = master_df[mask].copy()\n",
            "            print(f'After market filter ({MARKET_SCOPE}): {len(master_df)}')\n",
            "\n",
            "    # -- exclusion filters --\n",
            "    FINANCIAL_CATS = {'bank','insurance','leasing','securities','other_financial'}\n",
            "    if EXCLUDE_FINANCIAL and 'internal_category' in master_df.columns:\n",
            "        before = len(master_df)\n",
            "        master_df = master_df[~master_df['internal_category'].isin(FINANCIAL_CATS)].copy()\n",
            "        print(f'After excl. financials: {before} -> {len(master_df)}')\n",
            "\n",
            "    if EXCLUDE_ETF_REIT and 'quote_type' in master_df.columns:\n",
            "        before = len(master_df)\n",
            "        master_df = master_df[\n",
            "            ~master_df['quote_type'].str.lower().isin(['etf','reit','fund'])\n",
            "        ].copy()\n",
            "        print(f'After excl. ETF/REIT: {before} -> {len(master_df)}')\n",
            "\n",
            "    TICKERS = [\n",
            "        t for t in master_df['ticker'].dropna().unique().tolist()\n",
            "        if t and str(t).strip()\n",
            "    ]\n",
            "    print(f'\\nTarget tickers: {len(TICKERS)}')\n",
            "    print(f'First 10: {TICKERS[:10]}')\n"
        ]
    }

    # Inject cells at index 2 (after markdown 0 and config 1)
    new_cells = []
    new_cells.extend(nb['cells'][:2])
    new_cells.append(cell_imports)
    new_cells.append(cell_tickers)
    new_cells.extend(nb['cells'][2:])

    nb['cells'] = new_cells

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

if __name__ == \"__main__\":
    fix_notebook()
    print(\"Notebook fixed!\")
