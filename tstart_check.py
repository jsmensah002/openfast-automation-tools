import argparse
import glob
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument('pattern', help='glob for the .out files, e.g. "URef_*_seed*.out"')
p.add_argument('--col', required=True, help='output column to test, e.g. RotPwr')
p.add_argument('--ref', type=float, default=None, help='reference value (e.g. rated power); default = median of the column after the latest tstart')
p.add_argument('--factor', type=float, default=2, help='limit = factor x reference')
p.add_argument('--tstarts', nargs='+', type=float, default=[0, 5, 10, 15, 20, 25, 30], help='start times to test (s)')
a = p.parse_args()

runs = {}
for f in sorted(glob.glob(a.pattern)):
    runs[f] = pd.read_csv(f, sep=r'\s+', skiprows=[*range(6), 7])
if not runs:
    raise SystemExit('no files matched')

if a.ref is None:
    late = pd.concat([d[d['Time'] >= max(a.tstarts)][a.col] for d in runs.values()])
    ref = late.median()
else:
    ref = a.ref
limit = a.factor * ref
print(f'{len(runs)} runs | reference {ref:.1f} | limit = {a.factor:g} x reference = {limit:.1f}')

print('\ntstart  runs_above_limit  max_value')
for ts in a.tstarts:
    peaks = [d[d['Time'] >= ts][a.col].max() for d in runs.values()]
    print(f'{ts:>6g}  {sum(v > limit for v in peaks):>16}  {max(peaks):>9.1f}')

last = {f: d.loc[d[a.col] > limit, 'Time'].max() for f, d in runs.items()}
last = {f: t for f, t in last.items() if pd.notna(t)}
if last:
    worst = max(last, key=last.get)
    print(f'\nlatest time any run is above the limit: {last[worst]:.2f} s ({worst})')
else:
    print('\nno run goes above the limit at any time')
