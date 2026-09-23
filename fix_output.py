import argparse
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('fst')
a = p.parse_args()

path = Path(a.fst)
text = path.read_text()
new_text, n = re.subn(r'^(\s*)\d+(\s+OutFileFmt)', r'\g<1>1\g<2>', text, count=1, flags=re.MULTILINE)
if n:
    path.write_text(new_text)
    print(f'{a.fst}: OutFileFmt set to 1 (text output)')
else:
    print(f'{a.fst}: OutFileFmt line not found')
