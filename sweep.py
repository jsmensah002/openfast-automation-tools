import argparse
import re
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from scipy.stats import qmc

p = argparse.ArgumentParser()
p.add_argument('file')
p.add_argument('params', nargs='+', help='name=min:max')
p.add_argument('-n', type=int, required=True)
p.add_argument('--fst', default='AWT_YFix_WSt.fst')
p.add_argument('--workers', type=int, default=4)
a = p.parse_args()

names, bounds = [], []
for s in a.params:
    n, rng = s.split('=')
    lo, hi = (float(x) for x in rng.split(':'))
    names.append(n)
    bounds.append((lo, hi))

sampler = qmc.LatinHypercube(d=len(names), seed=42)
samples = qmc.scale(sampler.random(n=a.n), [b[0] for b in bounds], [b[1] for b in bounds])

case_dir = Path.cwd()
parent_dir = case_dir.parent

def run_one(i, values):
    label = '_'.join(f'{n}_{round(v,4)}' for n, v in zip(names, values))
    work_dir = parent_dir / f'sweep_tmp_{i}'
    work_dir.mkdir(exist_ok=True)
    for f in list(case_dir.glob('*.dat')) + list(case_dir.glob('*.fst')):
        shutil.copy(f, work_dir / f.name)
    file_path = work_dir / a.file
    with open(file_path) as fh:
        lines = fh.readlines()
    for n, v in zip(names, values):
        vs = str(round(v, 4))
        pat = re.compile(r'^(\s*)\S+(\s+' + re.escape(n) + r'\b)')
        for j, line in enumerate(lines):
            if pat.match(line):
                lines[j] = pat.sub(lambda m: m.group(1) + vs + m.group(2), line, count=1)
                break
        else:
            shutil.rmtree(work_dir, ignore_errors=True)
            return (i, label, False)
    with open(file_path, 'w') as fh:
        fh.writelines(lines)
    try:
        subprocess.run(['openfast', a.fst], check=True, cwd=work_dir,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copy(work_dir / a.fst.replace('.fst', '.out'), case_dir / f'{label}.out')
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
