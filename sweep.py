import argparse
import random
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
p.add_argument('--wind-file', default=None, help='InflowWind .dat file to repoint at the new .wnd (needed if sweeping TurbSim.inp)')
a = p.parse_args()

case_dir = Path.cwd()
parent_dir = case_dir.parent
fst_name = a.fst or next(f.name for f in case_dir.glob('*.fst'))
wind_file_name = a.wind_file or next((f.name for f in case_dir.glob('*InflowWind*.dat')), None)

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

uses_turbsim = any(f.endswith('.inp') for f in files)

sampler = qmc.LatinHypercube(d=len(names), seed=42)
samples = qmc.scale(sampler.random(n=a.n), [b[0] for b in bounds], [b[1] for b in bounds])

master_rng = random.Random(0)
seeds = [master_rng.randint(-2147483648, 2147483647) for _ in range(a.n)]

def point_wind(fpath, rootname):
    text = fpath.read_text()
    new_text, n = re.subn(r'"[^"]*"(\s+FileNameRoot)', f'"{rootname}"\\1', text, count=1)
    if n:
        fpath.write_text(new_text)
    return n > 0

def set_seed(fpath, seed):
    text = fpath.read_text()
    new_text, n = re.subn(r'^(\s*)-?\d+(\s+RandSeed1\b)', f'\\g<1>{seed}\\2', text, count=1, flags=re.MULTILINE)
    if n:
        fpath.write_text(new_text)
    return n > 0

def run_one(i, values, seed):
    label = '_'.join(f'{n}_{round(v,4)}' for n, v in zip(names, values))
    if uses_turbsim:
        label = f'{label}_seed{seed}'
    work_dir = parent_dir / f'sweep_tmp_{i}'
    work_dir.mkdir(exist_ok=True)
    for f in case_dir.iterdir():
        if f.is_file():
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

    if uses_turbsim:
        inp_name = next(f for f in files if f.endswith('.inp'))
        if not set_seed(work_dir / inp_name, seed):
            shutil.rmtree(work_dir, ignore_errors=True)
            return (i, label, False)
        try:
            subprocess.run(['turbsim', inp_name], check=True, cwd=work_dir,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            shutil.rmtree(work_dir, ignore_errors=True)
            return (i, label, False)
        rootname = inp_name.replace('.inp', '')
        if wind_file_name is None or not point_wind(work_dir / wind_file_name, rootname):
            shutil.rmtree(work_dir, ignore_errors=True)
            return (i, label, False)

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
    futures = [ex.submit(run_one, i, v, seeds[i]) for i, v in enumerate(samples)]
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
