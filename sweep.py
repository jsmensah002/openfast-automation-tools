import argparse
import re
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from scipy.stats import qmc
import subprocess

p = argparse.ArgumentParser()
p.add_argument('params', nargs='+', help='[file:]name=min:max — file carries over if omitted')
p.add_argument('-n', type=int, required=True)
p.add_argument('--fst', default=None)
p.add_argument('--workers', type=int, default=4)
a = p.parse_args()

case_dir = Path.cwd()
parent_dir = case_dir.parent
fst_name = a.fst or next(f.name for f in case_dir.glob('*.fst'))

files, names, bounds = [], [], []
current_file = None
for s in a.params:
    eq_pos = s.index('=')
    prefix = s[:eq_pos]
    rest = s[eq_pos+1:]
    if ':' in prefix:
        file_part, n = prefix.split(':', 1)
        current_file = file_part
    else:
        n = prefix
    if current_file is None:
        raise SystemExit('first parameter must include a file: prefix')
    lo, hi = (float(x) for x in rest.split(':'))
    files.append(current_file)
    names.append(n)
    bounds.append((lo, hi))

sampler = qmc.LatinHypercube(d=len(names), seed=42)
samples = qmc.scale(sampler.random(n=a.n), [b[0] for b in bounds], [b[1] for b in bounds])

def run_one(i, values):
    label = '_'.join(f'{n}_{round(v,4)}' for n, v in zip(names, values))
    work_dir = parent_dir / f'sweep_tmp_{i}'
    work_dir.mkdir(exist_ok=True)
    for f in list(case_dir.glob('*.dat')) + list(case_dir.glob('*.fst')):
        shutil.copy(f, work_dir / f.name)

    edited = {}
    for fname, n, v in zip(files, names, values):
        vs = str(round(v, 4))
        fpath = work_dir / fname
        lines = edited.get(fname) or fpath.read_text().splitlines(keepends=True)
        pat = re.compile(r'^(\s*)\S+(\s+' + re.escape(n) + r'\b)')
        for j, line in enumerate(lines):
            if pat.match(line):
                lines[j] = pat.sub(lambda m: m.group(1) + vs + m.group(2), line, count=1)
                break
        else:
            shutil.rmtree(work_dir, ignore_errors=True)
            return (i, label, False)
        edited[fname] = lines

    for fname, lines in edited.items():
        (work_dir / fname).write_text(''.join(lines))

    try:
        subprocess.run(['openfast', fst_name], check=True, cwd=work_dir,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copy(work_dir / fst_name.replace('.fst', '.out'), case_dir / f'{label}.out')
        ok = True
    except subprocess.CalledProcessError:
        ok = False
    shutil.rmtree(work_dir, ignore_errors=True)
    return (i, label, ok)

succeeded, failed = 0, []
with ThreadPoolExecutor(max_workers=a.workers) as ex:
    futures = [ex.submit(run_one, i, v) for i, v in enumerate(samples)]
    for fut in as_completed(futures):
        i, label, ok = fut.result()
        if ok:
            succeeded += 1
            print(f'[{i}] ok: {label}')
        else:
            failed.append(label)
            print(f'[{i}] FAILED: {label}')

print(f'\ndone: {succeeded} succeeded, {len(failed)} failed')
if failed:
    with open('sweep_failed.txt', 'w') as f:
        f.write('\n'.join(failed))
    print('failed runs logged to sweep_failed.txt')
