import argparse
import glob
import re
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument('pattern', help='e.g. "HWindSpeed_*_PropagationDir_*"')
p.add_argument('--cols', nargs='+', required=True, help='output columns to extract, e.g. RotTorq RootMyc1')
p.add_argument('--out', default='sweep_table.csv')
a = p.parse_args()

# turn pattern like HWindSpeed_*_PropagationDir_* into a regex that captures each * and remembers the param name before it
parts = a.pattern.split('*')
param_names = [re.match(r'.*?([A-Za-z]+)_?$', p).group(1) for p in parts[:-1]]
regex = re.escape(a.pattern).replace(r'\*', r'([\d.]+)')
regex = '^' + regex + r'\.out$'

rows = []
for f in glob.glob(a.pattern + '.out'):
    m = re.match(regex, f)
    if not m:
        continue
    row = {name: float(val) for name, val in zip(param_names, m.groups())}
    d = pd.read_csv(f, sep=r'\s+', skiprows=[*range(6), 7])
    for c in a.cols:
        row[f'{c}_mean'] = d[c].mean()
        row[f'{c}_peak'] = d[c].max()
    rows.append(row)

table = pd.DataFrame(rows).sort_values(param_names)
table.to_csv(a.out, index=False)
print(table)
