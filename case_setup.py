import argparse
import re
import shutil
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('case')
p.add_argument('--src', default='~/r-test/glue-codes/openfast')
a = p.parse_args()

src = Path(a.src).expanduser()
case_dir = src / a.case

siblings = set()
for f in list(case_dir.glob('*.fst')) + list(case_dir.glob('*.dat')):
    text = f.read_text(errors='ignore')
    for m in re.finditer(r'\.\./([A-Za-z0-9_]+)/', text):
        siblings.add(m.group(1))

shutil.copytree(case_dir, Path(a.case), dirs_exist_ok=True)
print(f'copied {a.case}')
for s in siblings:
    shutil.copytree(src / s, Path(s), dirs_exist_ok=True)
    print(f'copied {s} (needed by {a.case})')

if not siblings:
    print(f'{a.case} is self-contained, no sibling folders needed')
