"""Verify the published audit inputs and recorded output hashes without calling models."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def main():
    harness=json.loads((ROOT/'harness.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    spec=(ROOT/'SPECIFICATION.md').read_text(encoding='utf-8')
    if hashlib.sha256((ROOT/'SPECIFICATION.md').read_bytes()).hexdigest()!=manifest['source_sha256']:
        raise ValueError('Specification snapshot changed')
    checked=0
    for c in json.loads((ROOT/'cases.json').read_text(encoding='utf-8')):
        folder=ROOT/'cases'/c['id']
        history=json.loads((folder/'dialogue.json').read_text(encoding='utf-8'))
        turns=5 if c['extended'] else 3
        if len(history)!=2*turns:raise ValueError('Incomplete dialogue: '+c['id'])
        for i in range(1,turns+1):
            partial=history[:2*i-1]
            transcript='\n\n'.join(('ПОЛЬЗОВАТЕЛЬ' if x['role']=='user' else 'ПОМОЩНИК')+':\n'+x['text'] for x in partial)
            request=harness['improver_prefix']+spec+'\n\nСОСТОЯВШИЙСЯ РАЗГОВОР:\n'+transcript+'\n\nПродолжи одной репликой помощника.'
            name=f'answer-{i}'
            meta=json.loads((folder/(name+'.meta.json')).read_text(encoding='utf-8'))
            if not meta['success'] or digest(request)!=meta['input_sha256']:
                raise ValueError(f'Input reconstruction failed: {c["id"]}/{name}')
            if (folder/(name+'.txt')).read_text(encoding='utf-8')!=history[2*i-1]['text']:
                raise ValueError('Dialogue/answer mismatch')
            if hashlib.sha256((folder/(name+'.txt')).read_bytes()).hexdigest()!=meta['output_sha256']:
                raise ValueError('Answer hash mismatch')
            checked+=1
        final=history[-1]['text']
        blocks=re.findall(r'```(?:text|markdown|md)?\s*\n([\s\S]*?)\n```',final)
        extracted=(blocks[0] if len(blocks)==1 else final).strip()+'\n'
        if extracted!=(folder/'prompt.txt').read_text(encoding='utf-8'):
            raise ValueError('Final prompt extraction changed: '+c['id'])
        request=harness['executor_prefix']+extracted
        meta=json.loads((folder/'execution.meta.json').read_text(encoding='utf-8'))
        if not meta['success'] or digest(request)!=meta['input_sha256']:
            raise ValueError('Execution input mismatch: '+c['id'])
        if hashlib.sha256((folder/'execution.txt').read_bytes()).hexdigest()!=meta['output_sha256']:
            raise ValueError('Execution output mismatch: '+c['id'])
        checked+=1
    counts={'A':[],'B':[]}
    for folder in (ROOT/'reviews').iterdir():
        data=json.loads((folder/'parsed.json').read_text(encoding='utf-8'))
        raw=(folder/'review.txt').read_text(encoding='utf-8').strip()
        if raw.startswith('```'):raw='\n'.join(raw.splitlines()[1:-1])
        if json.loads(raw)!=data:raise ValueError('Parsed review differs from raw response')
        counts[folder.name[0]].extend(row['id'] for row in data['cases'])
        meta=json.loads((folder/'review.meta.json').read_text(encoding='utf-8'))
        request=(folder/'review.request.txt').read_text(encoding='utf-8')
        if not meta['success'] or digest(request)!=meta['input_sha256']:raise ValueError('Review input hash mismatch or unsuccessful review')
        if hashlib.sha256((folder/'review.txt').read_bytes()).hexdigest()!=meta['output_sha256']:
            raise ValueError('Review output hash mismatch')
    expected=[f'{i:02d}' for i in range(1,51)]
    if any(sorted(ids)!=expected for ids in counts.values()):raise ValueError('Reviews incomplete or duplicated')
    if checked!=220:raise ValueError('Unexpected model call count')
    print('Verified 170 briefing inputs/outputs, 50 executions, and two complete grading passes for 50 topics.')

if __name__=='__main__':main()
