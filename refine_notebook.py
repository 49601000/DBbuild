import json

file_path = r"c:\Users\info\MyAntigravity\02_hobby\04_qvt最適化ツール\tse_snapshot_day.ipynb"

def fix_notebook():
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'code':
            source = cell.get('source', [])
            new_source = []
            seen_imports = set()
            
            for line in source:
                # 1. root_path を db_path に一括置換
                fixed_line = line.replace('root_path', 'db_path')
                
                # 2. 重複した import を防ぐ (簡易的)
                if fixed_line.strip().startswith(('import ', 'from ')):
                    if fixed_line in seen_imports:
                        continue
                    seen_imports.add(fixed_line)
                
                new_source.append(fixed_line)
            
            cell['source'] = new_source
            
            # エラー出力をクリアして混乱を防ぐ
            if 'outputs' in cell:
                cell['outputs'] = []
            if 'execution_count' in cell:
                cell['execution_count'] = None

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    fix_notebook()
    print("Notebook refined and cleaned successfully!")
