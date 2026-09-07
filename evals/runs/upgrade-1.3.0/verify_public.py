"""Check public evidence integrity; no model, network, or agent execution."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
for name,digest in manifest['files'].items():
    path=(ROOT/name).resolve()
    assert path.is_relative_to(ROOT),name
    assert sha(path)==digest,name
count=0
for meta_path in ROOT.rglob('*.meta.json'):
    meta=json.loads(meta_path.read_text(encoding='utf-8'))
    answer=meta_path.with_name(meta_path.name.replace('.meta.json','.txt'))
    request=meta_path.with_name(meta_path.name.replace('.meta.json','.request.txt'))
    assert meta['success'],meta_path
    assert sha(answer)==meta['public_output_sha256'],answer
    assert sha(request)==meta['public_input_sha256'],request
    count+=1
assert count==42,count
assessment=json.loads((ROOT/'assessment.json').read_text(encoding='utf-8'))
assert len(assessment['cases'])==9
assert all(c['candidate_r2']=='pass' for c in assessment['cases'])
assert assessment['cases'][6]['baseline']=='fail'
assert assessment['cases'][6]['candidate']=='fail'
print(json.dumps({'files':len(manifest['files']),'model_calls':count,'integrity':'passed','behavior':'see primary-agent assessment and limitations'}))
