from pathlib import Path
import re
import sys
from load_data import load_database

# Корневая папка проекта находится выше папки scripts/.
root = Path(__file__).resolve().parent.parent

if len(sys.argv) != 2:
    raise SystemExit('Example: python3 scripts/run_queries.py analysis/01_data_quality.md')

# Находим внутри Markdown все блоки ```sql ... ```.
file_path = root / sys.argv[1]
markdown = file_path.read_text(encoding='utf-8')
blocks = re.findall(r'```sql\s*\n(.*?)\n```', markdown, flags=re.I | re.S)
if not blocks:
    raise SystemExit('No SQL blocks found in this Markdown file')

# Создаем временную базу из исходных CSV.
con = load_database(root)

# Выполняем SQL-блоки по порядку.
for i, block in enumerate(blocks, 1):
    print(f'\n--- Запрос {i} ---')
    # Внутри блока запросы разделяются точкой с запятой.
    for part in block.split(';'):
        # Строки-комментарии, начинающиеся с --, пропускаем.
        sql = '\n'.join(line for line in part.splitlines()
                        if not line.strip().startswith('--')).strip()
        if not sql:
            continue
        result = con.execute(sql)
        if result.description:  # SELECT возвращает строки: показываем первые 25.
            for row in result.fetchmany(25):
                print(tuple(row))
        else:
            print('ok')

con.close()
