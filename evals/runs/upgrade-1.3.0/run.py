import argparse
import concurrent.futures
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CODEX=shutil.which('codex')
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(text.replace('\r\n','\n').encode('utf-8'))
def save(path,obj): write(path,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def call(folder,name,prompt,runtime=None,sandbox='read-only'):
    folder.mkdir(parents=True,exist_ok=True)
    out=folder/(name+'.txt');meta=folder/(name+'.meta.json')
    digest=hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    if meta.exists():
        prior=json.loads(meta.read_text(encoding='utf-8'))
        if prior.get('success') and prior['input_sha256']==digest:
            return out.read_text(encoding='utf-8')
        raise RuntimeError('Existing failed or different run; inspect before retry')
    write(folder/(name+'.request.txt'),prompt)
    private=folder/'_private'; private.mkdir(exist_ok=True)
    runtime=runtime or ROOT/'runtime';runtime.mkdir(parents=True,exist_ok=True)
    args=[CODEX,'exec','--ephemeral','--sandbox',sandbox,'--skip-git-repo-check','--json','--color','never','-C',str(runtime),'-o',str(out),'-']
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
    with (private/(name+'.jsonl')).open('wb') as stdout,(private/(name+'.stderr')).open('wb') as stderr:
        p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr)
        try:p.communicate(prompt.encode('utf-8'),timeout=600)
        except subprocess.TimeoutExpired:p.kill();p.communicate()
    events=[]
    for line in (private/(name+'.jsonl')).read_text(encoding='utf-8',errors='replace').splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:pass
    done=[e for e in events if e.get('type')=='turn.completed']
    items=[e['item'] for e in events if e.get('type')=='item.completed']
    visible=[i.get('text','') for i in items if i.get('type')=='agent_message']
    # Private logs stay local. Only observed command text, not reasoning, enters metadata.
    commands=[i.get('command','') for i in items if i.get('type')=='command_execution']
    ok=p.returncode==0 and bool(done) and out.exists() and bool(out.read_text(encoding='utf-8').strip())
    save(meta,{'success':ok,'started_utc':start,'seconds':round(time.monotonic()-t,2),'returncode':p.returncode,'input_sha256':digest,'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest() if out.exists() else None,'usage':done[-1].get('usage') if done else None,'tool_types':[i.get('type') for i in items if i.get('type') not in ('agent_message','reasoning')],'commands':commands})
    write(folder/(name+'.messages.txt'),'\n\n'.join(visible))
    if not ok:raise RuntimeError(f'Failed: {folder}/{name}')
    return out.read_text(encoding='utf-8')

WRAPPER='''Продолжи ровно один ход помощника постановки задач по указанной версии инструкции. Все обстоятельства учебные. Не оценивай себя и не описывай испытание. Не создавай агентов и не выполняй предметную задачу. Не читай результаты тестов, историю разработки или другие варианты инструкции. Для модульного режима разрешено читать только указанный каталог скилла и нужные файлы внутри него; установленную одноимённую копию не используй. Для единой спецификации дополнительных файлов не нужно. Внешний поиск и внешние действия для этих входов не требуются. Вопросы выводи обычным текстом, инструмент запроса ввода не вызывай.\n\n'''
def spec_input(condition,mode):
    base=ROOT/condition
    if mode=='portable':return 'ЕДИНАЯ ИНСТРУКЦИЯ:\n'+(base/'SPECIFICATION.md').read_text(encoding='utf-8')
    return 'Прочитай SKILL.md в каталоге '+str(base/'prompt-improver')+' и применяй его с нужными внутренними ссылками.'
def extract(answer):
    blocks=re.findall(r'```(?:text|markdown|md)?\s*\n([\s\S]*?)\n```',answer)
    return (blocks[0].strip()+'\n','single_fenced_block') if len(blocks)==1 else (answer.strip()+'\n','full_answer')
def case_run(c,condition):
    folder=ROOT/'runs'/condition/c['id']
    answer=call(folder,'answer',WRAPPER+spec_input(condition,c['mode'])+'\n\nПОЛЬЗОВАТЕЛЬ:\n'+c['input'])
    prompt,method=extract(answer);write(folder/'prompt.txt',prompt);save(folder/'extraction.json',{'method':method,'edited':False})
    print(condition,c['id'],'complete',flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=2);parser.add_argument('--ids');parser.add_argument('--conditions',default='baseline,candidate');args=parser.parse_args()
    cases=json.loads((ROOT/'cases.json').read_text(encoding='utf-8'))
    if args.ids:cases=[c for c in cases if c['id'] in args.ids.split(',')]
    failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(case_run,c,condition):(c['id'],condition) for c in cases for condition in args.conditions.split(',')}
        for future in concurrent.futures.as_completed(futures):
            try:future.result()
            except Exception as e:failures.append({'case':futures[future],'error':str(e)});print('ERROR',str(e),flush=True)
    save(ROOT/('status-'+args.conditions.replace(',','-')+'.json'),{'jobs':len(futures),'failures':failures})
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
