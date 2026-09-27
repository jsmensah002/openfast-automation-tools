import argparse
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('file')
p.add_argument('rootname')
a = p.parse_args()

path = Path(a.file)
text = path.read_text()
new_text, n = re.subn(r'"[^"]*"(\s+FileNameRoot)', f'"{a.rootname}"\\1', text, count=1)
if n:
    path.write_text(new_text)
    print(f'{a.file}: FileNameRoot set to "{a.rootname}"')
else:
    print(f'{a.file}: FileNameRoot line not found')
