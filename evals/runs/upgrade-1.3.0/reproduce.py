"""Copy fixtures and skill snapshots to a NEW workspace before model runs."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,required=True,help='New directory; existing paths are refused')
p.add_argument('--conditions',default='baseline,candidate-r2')
p.add_argument('--ids',default=None)
p.add_argument('--workers',type=int,default=1)
a=p.parse_args()
target=a.out.resolve()
if target.exists():raise SystemExit('Choose a new output directory; existing evidence will not be overwritten.')
if not set(a.conditions.split(','))<= {'baseline','candidate','candidate-r2'}:raise SystemExit('Unknown condition')
target.mkdir(parents=True)
for name in ('baseline','candidate','candidate-r2'):
    shutil.copytree(ROOT/name,target/name)
for name in ('run.py','extra.py','cases.json','protocol.json'):
    shutil.copy2(ROOT/name,target/name)
args=[sys.executable,'-X','utf8',str(target/'run.py'),'--conditions',a.conditions,'--workers',str(a.workers)]
if a.ids:args+=['--ids',a.ids]
raise SystemExit(subprocess.call(args))
